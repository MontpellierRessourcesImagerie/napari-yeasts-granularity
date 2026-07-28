import numpy as np
from pathlib import Path
import tifffile as tiff


class DataLoader:

    root_labels_dir      = Path("/media/clement/fae534f3-f6ab-41aa-9554-baf3f7b791731/yeasts-granularity")
    root_intensities_dir = Path("/home/clement/Documents/projects/2292-yeasts-granularity/2026-05-11-tiff")
    root_results_dir     = Path("/media/clement/fae534f3-f6ab-41aa-9554-baf3f7b791731/results")

    def __init__(self, group_size=1, group_index=1, max_iter=float('inf')):
        if not self.root_labels_dir.exists():
            raise FileNotFoundError(f"Labels directory '{self.root_labels_dir}' does not exist.")
        if not self.root_intensities_dir.exists():
            raise FileNotFoundError(f"Intensities directory '{self.root_intensities_dir}' does not exist.")
        if not self.root_results_dir.exists():
            self.root_results_dir.mkdir(parents=True, exist_ok=True)
        
        self.images_list = []
        self.labels_list = []
        self.group_index = group_index
        self.group_size = group_size
        self.current_index = self.group_index - self.group_size
        self.step = self.group_size
        self.max_iter = max_iter
        self.current_image = None
        self.current_labels = None
        self.base_calib = {}
        self.n_iter = 0

        self._load_images_from_root()

    def get_results_path(self, what):
        current = self.images_list[self.current_index]
        folder = self.root_results_dir / current.relative_to(self.root_intensities_dir).parent
        self._ensure_path(folder, create_if_missing=True)
        return folder / f"{current.stem}_{what}.csv"

    def get_control_path(self, what):
        current = self.images_list[self.current_index]
        folder = self.root_results_dir / current.relative_to(self.root_intensities_dir).parent
        self._ensure_path(folder, create_if_missing=True)
        return folder / f"{current.stem}_{what}.tif"

    def set_base_calibration(self, calib_dict):
        self.base_calib = calib_dict

    def get_calibration(self, axes):
        calib = tuple(self.base_calib.get(ax, 1.0) for ax in axes)
        return calib

    def _load_images_from_root(self):
        for intensities_path in self.root_intensities_dir.rglob("*.tif"):
            label_path = self.root_labels_dir / intensities_path.relative_to(self.root_intensities_dir)
            self.images_list.append(intensities_path)
            self.labels_list.append(label_path)
        self.images_list.sort()
        self.labels_list.sort()
        self.current_index = self.group_index - self.group_size

    def _ensure_path(self, path, create_if_missing=False):
        if not path.exists():
            if create_if_missing:
                path.mkdir(parents=True, exist_ok=True)
            else:
                raise FileNotFoundError(f"Path '{path}' does not exist.")

    def next(self):
        if self.n_iter >= self.max_iter:
            print("Reached maximum number of iterations.")
            return False
        self.n_iter += 1
        if self.current_index < len(self.images_list) - self.step:
            self.current_index += self.step
        else:
            print("No more images to load.")
            return False
        print(f"Loaded image {self.current_index + 1}/{len(self.images_list)}: {self.images_list[self.current_index].name}")
        return True
    
    def load_image(self):
        if self.current_index >= len(self.images_list):
            raise IndexError("Current index is out of bounds.")
        img = tiff.imread(self.images_list[self.current_index])
        return img, ("ZYX" if img.ndim == 3 else "TZYX")
    
    def load_labels(self):
        if self.current_index >= len(self.labels_list):
            raise IndexError("Current index is out of bounds.")
        if not self.labels_list[self.current_index].exists():
            return (None, None)
        lbl = tiff.imread(self.labels_list[self.current_index])
        return lbl, ("ZYX" if lbl.ndim == 3 else "TZYX")
    
    def save_labels(self, labels):
        if self.current_index >= len(self.labels_list):
            raise IndexError("Current index is out of bounds.")
        folder = self.labels_list[self.current_index].parent
        self._ensure_path(folder, create_if_missing=True)
        tiff.imwrite(
            self.labels_list[self.current_index], 
            labels.astype(np.uint16),
            imagej=True,
            metadata={"axes": "TZYX" if labels.ndim == 4 else "ZYX"}
        )


if __name__ == "__main__":
    data_loader = DataLoader()
    while data_loader.next():
        image, image_axes = data_loader.load_image()
        labels, labels_axes = data_loader.load_labels()
        print(f"Image shape: {image.shape}, Labels shape: {labels.shape if labels is not None else 'None'}")
        print("=================")