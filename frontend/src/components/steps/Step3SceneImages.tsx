'use client';

import React, { useState } from 'react';
import { Card, Button, Input, ImageGrid, LoadingAnimation } from '@/components/ui';
import { apiClient } from '@/lib/api';
import { logger } from '@/lib/logger';
import { processImageResults } from '@/lib/imageHelpers';
import { Scene, APIException } from '@/lib/types';

interface Step3SceneImagesProps {
  polishedScript: string;
  onNext: (scenes: Scene[]) => void;
  onBack: () => void;
  initialScenes?: Scene[];
}

export const Step3SceneImages: React.FC<Step3SceneImagesProps> = ({
  polishedScript,
  onNext,
  onBack,
  initialScenes = [],
}) => {
  const [scenes, setScenes] = useState<Scene[]>(
    initialScenes.length > 0
      ? initialScenes
      : extractScenesFromScript(polishedScript)
  );
  const [generatingFor, setGeneratingFor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function extractScenesFromScript(script: string): Scene[] {
    // Simple extraction - look for scene headers
    // TODO: Backend - Create /api/v1/scripts/parse endpoint for better parsing
    const lines = script.split('\n');
    const sceneList: Scene[] = [];
    let sceneCounter = 1;

    lines.forEach((line) => {
      // Match patterns like "## Scene 1:" or "## 场景1:"
      const match = line.match(/^##\s*(Scene|场景)\s*(\d+)[\s:：]*(.*)/i);
      if (match) {
        const description = match[3] || `Scene ${sceneCounter}`;
        sceneList.push({
          id: `scene_${sceneCounter}`,
          description,
          location: extractLocation(description),
          time: extractTime(description),
          mode: 'generate',
          imageCount: 3,
          generatedImages: [],
          selectedImage: null,
        });
        sceneCounter++;
      }
    });

    // If no scenes found, create a default one
    if (sceneList.length === 0) {
      sceneList.push({
        id: 'scene_1',
        description: 'Main scene from the script',
        location: 'General setting',
        time: 'Day',
        mode: 'generate',
        imageCount: 3,
        generatedImages: [],
        selectedImage: null,
      });
    }

    return sceneList;
  }

  function extractLocation(description: string): string {
    // Simple heuristic to extract location
    const match = description.match(/(办公室|咖啡馆|室内|室外|公园|街道|office|cafe|indoor|outdoor|park|street)/i);
    return match ? match[0] : 'General setting';
  }

  function extractTime(description: string): string {
    // Simple heuristic to extract time
    const match = description.match(/(早晨|上午|中午|下午|傍晚|晚上|夜晚|morning|afternoon|evening|night|day)/i);
    return match ? match[0] : 'Day';
  }

  const handleGenerateImages = async (sceneId: string) => {
    const scene = scenes.find((s) => s.id === sceneId);
    if (!scene) return;

    logger.info('Step3SceneImages', `Generating images for scene: ${scene.description}`, {
      count: scene.imageCount,
    });

    setGeneratingFor(sceneId);
    setError(null);

    try {
      const imagePromises = Array.from({ length: scene.imageCount }).map(() =>
        apiClient.generateImage({
          prompt: `${scene.location}, ${scene.time}, ${scene.description}, cinematic lighting, high quality, establishing shot`,
          service: 'doubao',
          width: 1920,
          height: 1080,
          optimize_prompt: true,
        })
      );

      const results = await Promise.all(imagePromises);
      
      // Process image URLs, handling both URL and base64 responses
      const imageUrls = processImageResults(results);
      
      if (imageUrls.length === 0) {
        throw new Error('No valid images were generated. Please try again.');
      }

      setScenes((prev) =>
        prev.map((s) =>
          s.id === sceneId
            ? { ...s, generatedImages: imageUrls, selectedImage: imageUrls[0] }
            : s
        )
      );

      logger.info('Step3SceneImages', `Generated ${imageUrls.length} images for scene ${sceneId}`, {
        requested: scene.imageCount,
        received: imageUrls.length,
      });
    } catch (err) {
      logger.error('Step3SceneImages', `Failed to generate images for scene ${sceneId}`, err);
      
      if (err instanceof APIException) {
        setError(`Failed to generate images: ${err.message}`);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred. Please try again.');
      }
    } finally {
      setGeneratingFor(null);
    }
  };

  const handleImageSelect = (sceneId: string, imageUrl: string) => {
    setScenes((prev) =>
      prev.map((s) => (s.id === sceneId ? { ...s, selectedImage: imageUrl } : s))
    );
    logger.debug('Step3SceneImages', `Selected image for scene ${sceneId}`);
  };

  const handleFileUpload = async (sceneId: string, file: File) => {
    logger.info('Step3SceneImages', `Uploading image for scene ${sceneId}`);

    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      setScenes((prev) =>
        prev.map((s) =>
          s.id === sceneId
            ? {
                ...s,
                generatedImages: [dataUrl, ...s.generatedImages],
                selectedImage: dataUrl,
              }
            : s
        )
      );
    };
    reader.readAsDataURL(file);
  };

  const handleNext = () => {
    const missingScenes = scenes.filter((s) => !s.selectedImage);
    
    if (missingScenes.length > 0) {
      setError(
        `Please select or generate images for scenes: ${missingScenes.map((s) => s.id).join(', ')}`
      );
      return;
    }

    logger.info('Step3SceneImages', 'Proceeding to video generation step');
    onNext(scenes);
  };

  return (
    <div className="space-y-6">
      <Card>
        <p className="text-apple-body text-text-secondary">
          For each scene, generate reference images that capture the location, atmosphere, and
          time of day. These will serve as the base for video generation.
        </p>
      </Card>

      {/* Scene Cards */}
      <div className="space-y-6">
        {scenes.map((scene) => (
          <Card
            key={scene.id}
            title={scene.id}
            subtitle={`${scene.location} - ${scene.time}`}
          >
            <div className="space-y-4">
              <p className="text-apple-body text-text-primary">{scene.description}</p>

              {/* Mode Selection */}
              <div className="flex gap-4">
                <Button
                  variant={scene.mode === 'generate' ? 'primary' : 'secondary'}
                  size="sm"
                  onClick={() =>
                    setScenes((prev) =>
                      prev.map((s) =>
                        s.id === scene.id ? { ...s, mode: 'generate' } : s
                      )
                    )
                  }
                >
                  Auto Generate
                </Button>
                <Button
                  variant={scene.mode === 'upload' ? 'primary' : 'secondary'}
                  size="sm"
                  onClick={() =>
                    setScenes((prev) =>
                      prev.map((s) =>
                        s.id === scene.id ? { ...s, mode: 'upload' } : s
                      )
                    )
                  }
                >
                  Manual Upload
                </Button>
              </div>

              {/* Generate Mode */}
              {scene.mode === 'generate' && (
                <div className="flex gap-4 items-end">
                  <Input
                    label="Number of Images"
                    type="number"
                    min="1"
                    max="5"
                    value={scene.imageCount}
                    onChange={(e) =>
                      setScenes((prev) =>
                        prev.map((s) =>
                          s.id === scene.id
                            ? { ...s, imageCount: parseInt(e.target.value, 10) }
                            : s
                        )
                      )
                    }
                    className="w-32"
                  />
                  <Button
                    onClick={() => handleGenerateImages(scene.id)}
                    loading={generatingFor === scene.id}
                    disabled={generatingFor !== null}
                  >
                    Generate Images
                  </Button>
                </div>
              )}

              {/* Upload Mode */}
              {scene.mode === 'upload' && (
                <div>
                  <Input
                    type="file"
                    accept="image/*"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) {
                        handleFileUpload(scene.id, file);
                      }
                    }}
                  />
                </div>
              )}

              {/* Loading State */}
              {generatingFor === scene.id && (
                <LoadingAnimation message="Generating scene images..." />
              )}

              {/* Image Grid */}
              {scene.generatedImages.length > 0 && (
                <ImageGrid
                  images={scene.generatedImages.map((url) => ({
                    id: url,
                    url,
                    selected: url === scene.selectedImage,
                  }))}
                  onSelect={(imageUrl) => handleImageSelect(scene.id, imageUrl)}
                  columns={3}
                  aspectRatio="16/9"
                />
              )}
            </div>
          </Card>
        ))}
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-apple-red rounded-apple-md p-4">
          <p className="text-apple-red text-sm">{error}</p>
        </div>
      )}

      {/* Navigation */}
      <div className="flex justify-between">
        <Button onClick={onBack} variant="secondary" size="lg">
          ← Back
        </Button>
        <Button onClick={handleNext} size="lg">
          Next: Generate Video →
        </Button>
      </div>
    </div>
  );
};

export default Step3SceneImages;

