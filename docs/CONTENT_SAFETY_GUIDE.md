# Content Safety Guide

## Overview

This guide helps you understand and handle content safety errors when using AI generation services (Veo3, Midjourney, Nano Banana Pro).

## Common Safety Errors

### Veo3: PUBLIC_ERROR_UNSAFE_GENERATION

**What it means:** The Veo3 API detected content in your image or prompt that violates their content policy.

**Common triggers:**
- Violence or graphic content
- Inappropriate or suggestive imagery
- Copyrighted characters or logos
- Weapons or dangerous items prominently featured
- Medical or health-related misinformation
- Content depicting illegal activities

## Handling Safety Errors

### 1. Enable Graceful Failure (Recommended)

Configure your workflow to skip problematic scenes instead of crashing:

```python
from agents.orchestrator_agent import SimpleDramaGenerator

generator = SimpleDramaGenerator(
    config={
        'skip_failed_scenes': True,  # Skip scenes that fail safety checks
        'video_generator': {
            'skip_failed_scenes': True
        }
    }
)
```

With this enabled:
- Failed scenes will be logged with detailed error information
- The workflow will continue processing other scenes
- The final video will exclude problematic scenes
- You can review logs to identify and fix issues

### 2. Review Error Logs

When a scene fails, check the detailed error log:

```
Content safety error for scene scene_001:
  Image: output/images/scene_001_20260107_143000.png
  Scene description: A dark alley with mysterious figure...
  Location: Urban alley at night
  Error: Video generation failed: {'code': '', 'message': 'PUBLIC_ERROR_UNSAFE_GENERATION'}
  Suggestion: Review the scene content and image for policy violations
```

### 3. Inspect the Generated Image

The error log shows which image failed. Review it to identify issues:
- Open the image file listed in the error
- Look for content that might trigger safety filters
- Check for unintended elements in the generated image

## Avoiding Safety Errors

### Best Practices for Scene Descriptions

#### DO:
- Use neutral, descriptive language
- Focus on setting and atmosphere
- Describe emotions through facial expressions
- Use cinematic terminology (lighting, composition)
- Keep action descriptions general

```python
# Good example
scene = Scene(
    scene_id="scene_001",
    description="A cozy coffee shop interior with warm lighting. "
                "Character sits by window, looking thoughtful.",
    location="Coffee shop",
    time="Afternoon",
    shot_type=ShotType.MEDIUM_SHOT
)
```

#### DON'T:
- Describe violence or conflict in detail
- Include brand names or copyrighted content
- Use suggestive or inappropriate descriptions
- Mention weapons, drugs, or illegal activities
- Include medical procedures or injuries

```python
# Problematic example
scene = Scene(
    scene_id="scene_001",
    description="Character pulls out a weapon in the dark alley. "
                "Blood visible on the ground.",  # TOO GRAPHIC
    location="Dark alley",
    time="Night"
)
```

### Character Appearance Guidelines

When defining character appearances:

```python
# Safe character description
character = Character(
    name="Alex",
    appearance={
        "age": "25-30",
        "gender": "male",
        "build": "average",
        "clothing": "casual business attire",
        "hair": "short brown hair",
        "distinctive_features": "friendly smile"
    }
)
```

Avoid:
- Overly revealing clothing descriptions
- Emphasizing physical features excessively
- Descriptions that sexualize characters
- References to real celebrities or public figures

### Visual Style Considerations

Some visual styles are more likely to pass safety checks:

**Safer options:**
- "Professional photography"
- "Cinematic lighting"
- "Soft focus, natural colors"
- "Documentary style"
- "Animated, cartoon style"

**Use cautiously:**
- "Dark, gritty atmosphere" (can trigger warnings)
- "Horror style" (often flagged)
- "Intense action sequence" (may be rejected)

## Debugging Failed Scenes

### Step 1: Identify the Problem Scene

Check the error logs to find which scene failed:

```bash
grep "Content safety error" output/logs/generation.log
```

### Step 2: Review the Scene Definition

Examine your script for that scene:
- Is the description too graphic?
- Does it mention prohibited content?
- Are there unintended implications?

### Step 3: Modify the Scene

Options for fixing problematic scenes:

**Option A: Soften the description**
```python
# Before
description = "Character fights in brutal combat"

# After
description = "Character engages in martial arts training"
```

**Option B: Change the shot type**
```python
# Before
shot_type = ShotType.CLOSE_UP  # Shows detail that triggers filter

# After
shot_type = ShotType.LONG_SHOT  # More abstract, less detail
```

**Option C: Adjust visual style**
```python
# Before
visual_style = "dark, gritty, realistic"

# After
visual_style = "soft lighting, cinematic, professional"
```

### Step 4: Regenerate

After modifying the scene:

```python
# Regenerate just the problematic scenes
from agents.image_generator_agent import ImageGenerationAgent
from agents.video_generator_agent import VideoGenerationAgent

# Regenerate image
image_agent = ImageGenerationAgent()
new_image = await image_agent._generate_single_image(modified_scene)

# Regenerate video
video_agent = VideoGenerationAgent()
new_video = await video_agent._generate_video_clip(
    modified_scene,
    new_image['image_path']
)
```

## Configuration Reference

### Enable Error Skipping

In `.env`:
```bash
# No direct setting - configured in code
```

In your code:
```python
generator = SimpleDramaGenerator(
    config={
        'skip_failed_scenes': True,
        'video_generator': {
            'skip_failed_scenes': True
        }
    }
)
```

### Adjust Safety Settings (if available)

Some services may offer safety level settings:

```python
# Veo3 - currently no safety level parameter
# Midjourney - no direct control

# Nano Banana Pro - use less sensitive prompts
nano_config = {
    'model': 'sdxl',  # Different models may have different filters
}
```

## Service-Specific Guidelines

### Veo3 Video Generation
- Most strict about violence and inappropriate content
- Sensitive to weapons and dangerous items in images
- No way to adjust safety threshold
- **Solution:** Modify scenes before sending to Veo3

### Midjourney
- Generally permissive for artistic content
- Flags explicit content and violence
- Copyrighted characters may be rejected
- **Solution:** Use `--style` parameters to influence generation

### Nano Banana Pro
- Moderate safety filtering
- Less strict than video generation services
- Most flexible for creative content
- **Solution:** Usually not the bottleneck

## FAQ

### Q: Can I disable safety checks?
**A:** No, safety checks are enforced by the API providers and cannot be disabled.

### Q: What if my scene is legitimate but still rejected?
**A:** Try:
1. Rephrase the description more neutrally
2. Change the shot type to be less detailed
3. Adjust the visual style to be less intense
4. Use the skip feature and manually edit that scene later

### Q: How do I know which part of my scene triggered the error?
**A:**
1. Check the generated image - the issue is visible there
2. Review the scene description for problematic keywords
3. Try removing elements one at a time to isolate the trigger

### Q: Can I appeal a rejected scene?
**A:** No, these are automated checks by the API providers. Your options are to:
- Modify the content
- Skip the scene
- Use alternative generation methods

## Getting Help

If you're consistently hitting safety errors:

1. Review your script for patterns (violence, inappropriate content, etc.)
2. Check the `output/images/` directory to see what's being generated
3. Enable `skip_failed_scenes` to see how many scenes fail
4. Revise your story or scene descriptions accordingly

## Example: Fixing a Failed Scene

**Original scene that failed:**
```python
Scene(
    scene_id="scene_005",
    description="Two characters in heated confrontation, one pulls weapon",
    location="Dark warehouse",
    shot_type=ShotType.CLOSE_UP,
    visual_style="gritty, dark, intense"
)
```

**Revised scene that passes:**
```python
Scene(
    scene_id="scene_005",
    description="Two characters in tense conversation, standing apart",
    location="Warehouse interior",
    shot_type=ShotType.MEDIUM_SHOT,
    visual_style="cinematic, dramatic lighting"
)
```

**Key changes:**
- Removed weapon mention
- Made description less confrontational
- Changed to medium shot (less detail)
- Softened visual style
- Made location less ominous
