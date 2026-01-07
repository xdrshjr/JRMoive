"""
Grid image cropping utility for Midjourney 2x2 grid images
"""
from PIL import Image
from pathlib import Path
from typing import Union, Literal


def crop_grid_image(
    image_path: Union[str, Path],
    index: Literal[1, 2, 3, 4] = 1,
    output_path: Union[str, Path, None] = None
) -> Image.Image:
    """
    Crop a Midjourney 2x2 grid image to extract a single variation

    Args:
        image_path: Path to the grid image
        index: Which variation to extract (1=top-left, 2=top-right, 3=bottom-left, 4=bottom-right)
        output_path: Optional path to save the cropped image. If None, returns PIL Image object

    Returns:
        PIL Image object of the cropped single image

    Raises:
        FileNotFoundError: If image_path doesn't exist
        ValueError: If index is not 1-4

    Example:
        >>> # Crop top-left image and save
        >>> cropped = crop_grid_image("output/grid.png", index=1, output_path="output/single.png")

        >>> # Crop and return PIL Image for further processing
        >>> img = crop_grid_image("output/grid.png", index=2)
        >>> img.resize((1920, 1080)).save("output/resized.png")
    """
    if index not in [1, 2, 3, 4]:
        raise ValueError(f"Index must be 1, 2, 3, or 4, got {index}")

    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Load image
    img = Image.open(image_path)
    width, height = img.size

    # Calculate crop dimensions (assuming 2x2 grid)
    crop_width = width // 2
    crop_height = height // 2

    # Define crop positions
    positions = {
        1: (0, 0, crop_width, crop_height),  # Top-left
        2: (crop_width, 0, width, crop_height),  # Top-right
        3: (0, crop_height, crop_width, height),  # Bottom-left
        4: (crop_width, crop_height, width, height)  # Bottom-right
    }

    # Crop the image
    box = positions[index]
    cropped = img.crop(box)

    # Save if output path provided
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cropped.save(output_path)
        print(f"Cropped image saved to: {output_path}")

    return cropped


def batch_crop_grid_images(
    input_dir: Union[str, Path],
    output_dir: Union[str, Path],
    index: Literal[1, 2, 3, 4] = 1,
    pattern: str = "*.png"
) -> list[Path]:
    """
    Batch crop all grid images in a directory

    Args:
        input_dir: Directory containing grid images
        output_dir: Directory to save cropped images
        index: Which variation to extract (1-4)
        pattern: File pattern to match (default: "*.png")

    Returns:
        List of paths to cropped images

    Example:
        >>> # Crop all grid images in output/scenes to output/scenes_cropped
        >>> cropped_files = batch_crop_grid_images(
        ...     "output/scenes",
        ...     "output/scenes_cropped",
        ...     index=1
        ... )
        >>> print(f"Processed {len(cropped_files)} images")
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cropped_paths = []

    # Process all matching files
    for image_path in input_dir.glob(pattern):
        output_path = output_dir / image_path.name
        cropped = crop_grid_image(image_path, index=index, output_path=output_path)
        cropped_paths.append(output_path)

    print(f"Batch processed {len(cropped_paths)} images from {input_dir} to {output_dir}")
    return cropped_paths


if __name__ == "__main__":
    # Demo usage
    import sys

    if len(sys.argv) < 2:
        print("Usage: python grid_cropper.py <grid_image_path> [index] [output_path]")
        print("  index: 1=top-left, 2=top-right, 3=bottom-left, 4=bottom-right (default: 1)")
        print("\nExample:")
        print("  python grid_cropper.py output/test_grid.png 1 output/test_single.png")
        sys.exit(1)

    image_path = sys.argv[1]
    index = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    output_path = sys.argv[3] if len(sys.argv) > 3 else None

    if output_path is None:
        # Auto-generate output path
        input_path = Path(image_path)
        output_path = input_path.parent / f"{input_path.stem}_cropped_{index}{input_path.suffix}"

    cropped = crop_grid_image(image_path, index=index, output_path=output_path)
    print(f"[SUCCESS] Cropped image size: {cropped.size}")
