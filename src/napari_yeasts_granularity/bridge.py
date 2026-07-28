import xarray as xr
from napari.layers.labels.labels import Labels
from napari.layers.image.image import Image


class NapariBridge:

    allowed_axes = set({'T', 'Z', 'Y', 'X'})

    @staticmethod
    def _get_layer_as_xarray(viewer, layer_name, layer_type):
        if layer_name not in viewer.layers:
            raise ValueError(f"Layer '{layer_name}' not found in the viewer.")
        layer = viewer.layers[layer_name]
        if not isinstance(layer, layer_type):
            raise TypeError(f"Layer '{layer_name}' is not of type {layer_type.__name__}.")
        data = layer.data
        scale = layer.scale
        axes = layer.axis_labels
        if data.ndim != len(axes):
            raise ValueError(f"Data dimensions {data.ndim} do not match axes length {len(axes)}")
        if len(scale) != len(axes):
            raise ValueError(f"Scale length {len(scale)} does not match axes length {len(axes)}")
        current_axes = set(axes)
        if not current_axes.issubset(NapariBridge.allowed_axes):
            raise ValueError(f"Axes {current_axes} are not a subset of allowed axes {NapariBridge.allowed_axes}")
        return xr.DataArray(
            data, 
            dims=list(axes),
            attrs={a: s for a, s in zip(axes, scale)}
        ), scale

    @staticmethod
    def get_labels_as_xarray(viewer, layer_name):
        return NapariBridge._get_layer_as_xarray(viewer, layer_name, Labels)

    @staticmethod
    def get_image_as_xarray(viewer, layer_name):
        return NapariBridge._get_layer_as_xarray(viewer, layer_name, Image)

    @staticmethod
    def xarray_to_labels_layer(viewer, xarray_data, layer_name):
        data = xarray_data.values
        scale = [xarray_data.attrs.get(dim, 1.0) for dim in xarray_data.dims]
        axes = [str(a) for a in xarray_data.dims]
        return viewer.add_labels(
            data, 
            name=layer_name, 
            scale=scale, 
            axis_labels=axes
        )