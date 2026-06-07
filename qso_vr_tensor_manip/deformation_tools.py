from __future__ import annotations


class TensorDeformation:
    @staticmethod
    def stretch(tensor, axis=0, factor=1.2):
        _ = axis
        _ = factor
        return tensor

    @staticmethod
    def rotate(tensor, axes=(0, 1), angle=0.0):
        _ = axes
        _ = angle
        return tensor

    @staticmethod
    def compress(tensor, axis=0, factor=0.8):
        _ = axis
        _ = factor
        return tensor

    @staticmethod
    def split(tensor, axis=0):
        _ = axis
        return tensor, tensor
