# napari-yeasts-granularity

This Napari plugin extracts various measurements from a time series of fluorescent yeast nuclei to estimate the granularity of each nucleus over time.

All nuclei are segmented and tracked over time. Measurements such as the standard deviation of raw intensities, the standard deviation of the DoG result, the volume, and the number of local maxima are then extracted.

## I. Install

- You need to install Napari yourself beforehand.
`napari-yeasts-granularity` is still in an experimental phase and not yet available on PyPI. To install it, you can either:
- Use Git and run `pip install -e git+https://github.com/MontpellierRessourcesImagerie/napari-yeasts-granularity.git`
- Download a frozen version from the [GitHub repository](https://github.com/MontpellierRessourcesImagerie/napari-yeasts-granularity) and install it with `pip install -e /path/to/the/folder/you/downloaded`

## II.1. Usage from Napari

### A. Calibration

- Open Napari and load one of your images in the viewer.
- You need at least the image you will segment and the one used for measurement (which can be the same image). Optionally, you can also have an image against which colocalization will be measured.
- If your screen is large enough, you can open both the "Yeast granularity" and "Feature table" widgets from the "Plugins" menu at the same time.
- In the "Calibration" widget, indicate the physical size of your pixels on the X, Y, and Z axes. In the axes dropdown menu, specify that your images are 3D+t stacks, corresponding to "TZYX".
- Apply this to all your images.

### B. Segment & track your nuclei

Move to the "Segment nuclei" widget in the right column and adjust the settings:
- `Input`: The image used to segment nuclei.
- `Gaussian σ`: The blur applied as a prefilter for segmentation only (the blurred image is not used for the measurements). It removes inner structures that could create holes in the segmented nuclei.
- `Log factor`: Increase this value if there is a large intensity gap between your dimmest and brightest nuclei. For segmentation, intensities are normalized between 0.0 and 1.0 before being multiplied by this factor. The logarithm of the result is then taken, because the log curve flattens intensities past the inflection point — this factor lets more values pass that inflection point.
- `Kill borders?`: Removes all nuclei that touch the border at any point in time.
- `Min. object size`: Used to remove debris. All objects smaller than this number of voxels will be removed.
- `Diameter`: Used for tracking. Should be approximately the diameter of a nucleus. If a nucleus moves more than this distance between two consecutive time points, it will be considered lost.

Click "Apply"; a spinning wheel will appear in the lower right corner of Napari while the process runs. Once finished, a new layer named after the image with the "_nuclei" suffix will appear in your layers list.

**Note:** You can adjust the settings by trial and error and reapply this function as many times as needed.

### C. Measure inside nuclei

Move to the "Measure nuclei" widget and adjust the settings:
- `Intensities`: The original image in which granularity will be evaluated.
- `Nuclei`: The layer containing the nuclei segmented in the previous step.
- `Use intensities?`: Whether intensity-based metrics will be extracted ("Mean", "Std. Dev.", "Q1", "Q3", "IQR", "Mean (DoG)", "Std. Dev. (DoG)", "Q1 (DoG)", "Q3 (DoG)", "IQR (DoG)").
- `Use shape?`: Whether shape-based metrics will be extracted ("Volume", "Solidity", "Sphericity").
- `Use spots?`: Whether spots (local maxima) will be counted and extracted.
- `Min. prominence`: Minimum prominence required for a local maximum to be considered an actual spot. Too high a value will miss spots; too low a value will capture noise.
- `Colocalization`: Colocalization analysis is optional and can be turned off with the checkbox on the left. If enabled, select in the combo box the channel against which colocalization will be evaluated.

Once these settings are adjusted, click "Apply" and wait for the spinning wheel to disappear. Some operations can take a while (2–3 minutes), but you can follow progress in the terminal.

**Note:** To visualize the results, open the "Features table" widget from the "Plugins" menu and click on the layer containing the segmented nuclei. From this widget, you can export the measurements to a CSV file.

## II.2. Usage from the notebook

A notebook is available in the "notebooks" folder and lets you process an entire folder hierarchy from a root directory. Simply provide the path to the root of the hierarchy and the location where results should be saved. The code is visible but does not need to be edited. The notebook can be run in the same environment as the Napari plugin if you install the `notebook` package (`pip install notebook`).

Launch the Jupyter server with the command `jupyter notebook`, then navigate through your folders until you find the `.ipynb` file.

## III. Measurements description

These metrics are computed from the local intensities of each individual nucleus. Only the voxels belonging to a given nucleus, according to the segmentation, are considered (not a bounding box or anything else). When nothing follows the metric name (e.g., "Mean"), the metric was computed on the raw image. When a suffix is present (e.g., "Mean (DoG)"), the metric was computed on a filtered image, and the suffix names the filter used (here, "DoG" stands for "Difference of Gaussians").

The "Difference of Gaussians" filter is a band-pass filter. A small Gaussian is applied to the raw image to remove noise. At the same time, a large Gaussian is applied to isolate the base signal of the nuclei (≈ an estimate of the background). Finally, the result of the large Gaussian is subtracted from the result of the small Gaussian, leaving only the structures of interest. The resulting image should be exactly 0 where there is nothing, containing only structures that were not destroyed by the small Gaussian and are not part of the nuclei's baseline signal.

<img width="1230" height="693" alt="DoG" src="https://github.com/user-attachments/assets/d0ab35ac-5fd3-4204-b93a-d83fa65b1986" />

- **"Mean" and "Std. Dev."**: The mean and standard deviation of the values belonging to the nucleus. We expect the standard deviation to increase as granularity increases.
- **"Q1" and "Q3"**: The 25th and 75th percentiles when all pixels belonging to the nucleus are sorted in ascending order. We expect Q1 to decrease and Q3 to increase as granularity increases (a lower Q1 and a higher Q3).
- **"IQR"**: Interquartile range — the distance between Q1 and Q3. We expect it to increase with granularity.
- **"Volume"**: Volume in µm³ of each nucleus, based on the number of voxels multiplied by the physical volume of one voxel.
- **"Solidity"**: Ratio of the object's volume to its convex hull volume. If the object is convex, the value is 1.0; the less convex it is, the closer the value tends toward 0.0.
- **"Sphericity"**: Ratio of the object's volume to the volume of the smallest sphere able to contain it. If the object is a sphere, this equals 1.0, tending toward 0.0 the less spherical it is.
- **"Num. spots"**: Number of local maxima with a prominence greater than the user-provided threshold (see figure below, where prominences are noted P1 and P2).

<img width="1000" height="337" alt="prominence" src="https://github.com/user-attachments/assets/4eeadb0a-c1ee-4f7a-bee7-0f0a057bbee7" />


- **"Pearson"**: Indicates whether the two channels follow the same trend. It tends toward 1.0 when a pixel that is high in C1 is also high in C2, or low in C1 and also low in C2. Conversely, it tends toward -1.0 when an increase in one channel corresponds to a decrease in the other. A value of 0.0 means the channels are uncorrelated.
- **"p-value"**: Indicates how likely it is that the Pearson score for this nucleus arose by chance if there were actually no correlation. A p-value below 0.05 is generally considered statistically significant.
