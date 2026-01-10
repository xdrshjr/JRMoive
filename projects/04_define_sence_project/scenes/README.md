# Custom Scene Base Images

This folder is for storing custom base images for scenes and sub-scenes in your project.

## Overview

Instead of generating scene images via AI, you can provide your own custom base images. The system will use these images directly for video generation, giving you full control over the visual appearance of your scenes.

## Usage

### 1. Specify Custom Image in Script

In your `script.txt`, add the `场景图:` field to specify the custom base image filename:

```
## 场景1：逼仄的贫民窟出租屋
地点: 狭小昏暗的出租屋
时间: 深夜
...
场景图: scene_001_base.png
```

For sub-scenes:

```
### 子场景1-1：桌面特写
描述: 特写桌面上堆积如山的空泡面桶
...
场景图: scene_001_sub_001_base.png
```

### 2. Place Images in This Folder

Place your custom images in this `scenes/` folder with the exact filename specified in the script:

```
projects/04_define_sence_project/
├── script.txt
├── config.yaml
└── scenes/
    ├── README.md (this file)
    ├── scene_001_base.png
    └── scene_001_sub_001_base.png
```

### 3. Run Generation

When you run the generation, the system will:
- Check if the scene/sub-scene has a `场景图` field
- Load the image from this folder
- Use it directly for video generation
- Fall back to AI generation if the image is not found

## Image Requirements

- **Format**: PNG, JPG, or other common image formats
- **Resolution**: Recommended 1920x1080 (or match your project config)
- **Quality**: High quality images for best video results
- **Content**: Should match the scene description in your script

## Naming Conventions

We recommend the following naming convention for clarity:

- **Main scenes**: `scene_001_base.png`, `scene_002_base.png`, etc.
- **Sub-scenes**: `scene_001_sub_001_base.png`, `scene_001_sub_002_base.png`, etc.

You can use any filename you prefer, as long as it matches what's specified in `script.txt`.

## Example Workflow

1. Write your script with scene descriptions
2. Generate the project once with AI (optional, to see what it looks like)
3. Create/edit custom images for specific scenes
4. Place custom images in the `scenes/` folder
5. Add `场景图:` field to those scenes in `script.txt`
6. Re-generate the project

## Benefits

- **Full artistic control** over scene appearance
- **Consistency** across multiple regenerations
- **Pre-made assets** can be reused across projects
- **Mix and match**: Use custom images for some scenes, AI for others

## Troubleshooting

**Problem**: "Custom base image not found" error

**Solution**: 
- Verify the filename in `script.txt` matches the file in this folder exactly (including extension)
- Check for typos or case sensitivity issues
- Ensure the file is actually in the `scenes/` folder

**Problem**: Video quality is poor

**Solution**:
- Use higher resolution images (1920x1080 or better)
- Ensure images are not compressed or low quality
- Match the aspect ratio specified in your project config

## Notes

- Custom images are **optional** - scenes without `场景图:` field will be AI-generated as usual
- The system will log which scenes use custom images vs AI generation
- Custom images are copied to the output directory during generation

