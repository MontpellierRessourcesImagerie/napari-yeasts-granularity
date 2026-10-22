
var inputRoot = "";
var outputRoot = "";
var vsiCount = 0;


function scanDirectory(currentDir) {
    list = getFileList(currentDir);

    for (i = 0; i < list.length; i++) {
        item = list[i];

        if (endsWith(item, "/")) {
            folderName = substring(item, 0, lengthOf(item) - 1);

            if (startsWith(folderName, "_")) {
                continue;
            }

            scanDirectory(currentDir + item);

        } else if (endsWith(toLowerCase(item), ".vsi")) {
            processVsiFile(currentDir + item);
        }
    }
}

function processVsiFile(vsiPath) {
    vsiCount++;

    relativePath = substring(vsiPath, lengthOf(inputRoot));

    relativeDir = File.getDirectory(vsiPath);
    relativeDir = substring(relativeDir, lengthOf(inputRoot));
    outputDir = outputRoot + relativeDir;

    if (!File.exists(outputDir)) {
        File.makeDirectory(outputDir);
        ensureDirectoryExists(outputDir);
    }

    fileName = File.getName(vsiPath);
    print("[" + vsiCount + "] Trouvé : " + vsiPath);
    output_path = outputDir + fileName;
    print("    -> Sortie prévue dans : " + output_path);

    run("Bio-Formats", "open=["+vsiPath+"] color_mode=Default rois_import=[ROI manager] view=Hyperstack stack_order=XYCZT series_1");
    saveAs("TIFF", output_path);
    run("Close All");
}

function ensureDirectoryExists(dir) {
    if (File.exists(dir)) {
        return;
    }
    parent = File.getParent(dir);
    if (!File.exists(parent)) {
        ensureDirectoryExists(parent);
    }
    File.makeDirectory(dir);
}

function main() {
	setBatchMode("hide");
    inputRoot = getDirectory("Choisir le dossier racine d'entrée (contenant les .vsi)");
    outputRoot = getDirectory("Choisir le dossier racine de sortie");

    if (inputRoot == "" || outputRoot == "") {
        exit("Sélection annulée, arrêt de la macro.");
    }

    print("=== Début du scan ===");
    print("Entrée  : " + inputRoot);
    print("Sortie  : " + outputRoot);
    print("----------------------------------------");

    vsiCount = 0;
    scanDirectory(inputRoot);

    print("----------------------------------------");
    print("=== Scan terminé : " + vsiCount + " fichier(s) .vsi trouvé(s) ===");
    setBatchMode("exit and display");
}

main();