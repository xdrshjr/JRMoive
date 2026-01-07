"""
Complete workflow example: Midjourney with automatic grid cropping

This example shows how to use Midjourney for image generation
and automatically crop grid images to single images.
"""
import asyncio
from pathlib import Path
from agents.image_generator_agent import ImageGenerationAgent
from utils.grid_cropper import crop_grid_image
from models.script_models import Scene, ShotType, CameraMovement


async def generate_with_auto_crop():
    """Generate images with Midjourney and auto-crop grids to single images"""

    print("=" * 60)
    print("Midjourney + Auto-Crop Workflow Example")
    print("=" * 60)

    # Create sample scenes
    scenes = [
        Scene(
            scene_id="scene_001",
            location="Modern office",
            time="Morning",
            description="A programmer sitting at desk with multiple monitors, typing code",
            duration=3.0,
            shot_type=ShotType.MEDIUM_SHOT,
            camera_movement=CameraMovement.STATIC,
            visual_style="Modern tech",
            atmosphere="Focused"
        ),
        Scene(
            scene_id="scene_002",
            location="Coffee shop",
            time="Afternoon",
            description="Developer having a discussion with colleague over laptop",
            duration=2.5,
            shot_type=ShotType.CLOSE_UP,
            camera_movement=CameraMovement.PAN,
            visual_style="Casual warm",
            atmosphere="Collaborative"
        )
    ]

    # Step 1: Generate grid images with Midjourney
    print("\nStep 1: Generating grid images with Midjourney...")
    print(f"  Scenes to generate: {len(scenes)}")

    grid_output_dir = Path("./output/examples/grids")
    agent = ImageGenerationAgent(
        service_type="midjourney",
        output_dir=grid_output_dir,
        config={'max_concurrent': 2}
    )

    try:
        # Progress callback
        async def on_progress(progress: float, message: str):
            print(f"  Progress: {progress:.1f}% - {message}")

        # Generate grid images
        results = await agent.execute_concurrent(
            scenes,
            progress_callback=on_progress
        )

        print(f"\n[SUCCESS] Generated {len(results)} grid images")

        # Step 2: Crop all grid images to single images
        print("\nStep 2: Cropping grids to single images...")

        single_output_dir = Path("./output/examples/singles")
        single_output_dir.mkdir(parents=True, exist_ok=True)

        cropped_results = []
        for i, result in enumerate(results, 1):
            grid_path = Path(result['image_path'])
            single_path = single_output_dir / f"{result['scene_id']}_single.png"

            # Crop top-left image (index=1)
            # You can configure which quadrant to use: 1-4
            print(f"  [{i}/{len(results)}] Cropping {grid_path.name}...")
            cropped = crop_grid_image(
                grid_path,
                index=1,  # Use top-left variation
                output_path=single_path
            )

            cropped_results.append({
                'scene_id': result['scene_id'],
                'grid_path': str(grid_path),
                'single_path': str(single_path),
                'size': cropped.size
            })

        print(f"\n[SUCCESS] Cropped {len(cropped_results)} images")

        # Step 3: Display results
        print("\n" + "=" * 60)
        print("Results Summary")
        print("=" * 60)

        for i, result in enumerate(cropped_results, 1):
            print(f"\nScene {i}: {result['scene_id']}")
            print(f"  Grid image:   {result['grid_path']}")
            print(f"  Single image: {result['single_path']}")
            print(f"  Size: {result['size'][0]}x{result['size'][1]}")

        print("\n" + "=" * 60)
        print(f"Complete! {len(cropped_results)} single images ready for video generation")
        print("=" * 60)

        return cropped_results

    except Exception as e:
        print(f"\n[ERROR] Workflow failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await agent.close()


async def main():
    """Run the complete workflow"""
    results = await generate_with_auto_crop()

    if results:
        print("\n[INFO] Next steps:")
        print("  1. Review the single images in output/examples/singles/")
        print("  2. Use these images for video generation")
        print("  3. Continue with VideoGenerationAgent and VideoComposerAgent")


if __name__ == "__main__":
    asyncio.run(main())
