/**
 * NEXUS AI File Chunker Utility
 * Splits large datasets (>50MB) into balanced parts with preserved CSV headers
 * and clean newline boundaries so every chunk is a valid, independently indexable dataset.
 */

export async function splitFileIntoChunks(file, targetChunkMb = 25) {
  const targetChunkBytes = targetChunkMb * 1024 * 1024;
  const totalSize = file.size;

  if (totalSize <= targetChunkBytes) {
    return [file];
  }

  const lastDot = file.name.lastIndexOf(".");
  const baseName = lastDot !== -1 ? file.name.substring(0, lastDot) : file.name;
  const ext = (lastDot !== -1 ? file.name.substring(lastDot) : "").toLowerCase();

  // If CSV, handle newline-aware splitting with header preservation
  if (ext === ".csv" || file.type === "text/csv") {
    return await splitCsvFile(file, baseName, ext, targetChunkBytes);
  }

  // Fallback for general text or binary files
  return await splitBinaryFile(file, baseName, ext, targetChunkBytes);
}

async function splitCsvFile(file, baseName, ext, targetChunkBytes) {
  const totalSize = file.size;
  
  // 1. Read first 64KB to extract the CSV header line
  const headerSlice = file.slice(0, 65536);
  const headerText = await headerSlice.text();
  const firstNewlineIdx = headerText.indexOf("\n");
  
  let headerString = "";
  let headerBlob = null;
  if (firstNewlineIdx !== -1) {
    headerString = headerText.slice(0, firstNewlineIdx + 1); // includes \n
    headerBlob = new Blob([headerString], { type: "text/csv" });
  }

  const parts = [];
  let currentStart = 0;
  let partNumber = 1;

  while (currentStart < totalSize) {
    let targetEnd = Math.min(currentStart + targetChunkBytes, totalSize);

    // If not at the end of the file, search backwards for the nearest newline
    // so we never cut a CSV row in half!
    if (targetEnd < totalSize) {
      const windowStart = Math.max(currentStart, targetEnd - 65536);
      const windowBlob = file.slice(windowStart, Math.min(totalSize, targetEnd + 65536));
      const windowText = await windowBlob.text();
      
      const offsetInWindow = targetEnd - windowStart;
      const lastNewline = windowText.lastIndexOf("\n", offsetInWindow);
      if (lastNewline !== -1 && (windowStart + lastNewline) > currentStart) {
        targetEnd = windowStart + lastNewline + 1; // Include newline
      }
    }

    const dataSlice = file.slice(currentStart, targetEnd);
    let finalPartBlob;

    if (partNumber === 1 || !headerBlob) {
      // Part 1 already has the original header
      finalPartBlob = dataSlice;
    } else {
      // Prepend the exact CSV header to Part 2, Part 3, etc.
      // This ensures DuckDB recognizes the exact same column schema across all parts!
      finalPartBlob = new Blob([headerBlob, dataSlice], { type: "text/csv" });
    }

    const partFilename = `${baseName}_part_${partNumber}${ext}`;
    const partFile = new File([finalPartBlob], partFilename, {
      type: file.type || "text/csv",
      lastModified: Date.now()
    });

    parts.push(partFile);
    currentStart = targetEnd;
    partNumber++;
  }

  return parts;
}

async function splitBinaryFile(file, baseName, ext, targetChunkBytes) {
  const totalSize = file.size;
  const parts = [];
  let currentStart = 0;
  let partNumber = 1;

  while (currentStart < totalSize) {
    const targetEnd = Math.min(currentStart + targetChunkBytes, totalSize);
    const slice = file.slice(currentStart, targetEnd);
    const partFilename = `${baseName}_part_${partNumber}${ext}`;
    const partFile = new File([slice], partFilename, {
      type: file.type || "application/octet-stream",
      lastModified: Date.now()
    });
    parts.push(partFile);
    currentStart = targetEnd;
    partNumber++;
  }

  return parts;
}
