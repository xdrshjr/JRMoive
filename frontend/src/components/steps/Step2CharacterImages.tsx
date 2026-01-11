'use client';

import React, { useState } from 'react';
import { Card, Button, Input, ImageGrid, LoadingAnimation } from '@/components/ui';
import { apiClient } from '@/lib/api';
import { logger } from '@/lib/logger';
import { Character, APIException } from '@/lib/types';

interface Step2CharacterImagesProps {
  polishedScript: string;
  onNext: (characters: Character[]) => void;
  onBack: () => void;
  initialCharacters?: Character[];
}

export const Step2CharacterImages: React.FC<Step2CharacterImagesProps> = ({
  polishedScript,
  onNext,
  onBack,
  initialCharacters = [],
}) => {
  const [characters, setCharacters] = useState<Character[]>(
    initialCharacters.length > 0
      ? initialCharacters
      : extractCharactersFromScript(polishedScript)
  );
  const [generatingFor, setGeneratingFor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function extractCharactersFromScript(script: string): Character[] {
    // Simple extraction - look for character names in dialogue format
    // TODO: Backend - Create /api/v1/scripts/parse endpoint for better parsing
    const lines = script.split('\n');
    const characterNames = new Set<string>();

    lines.forEach((line) => {
      // Match patterns like "Character Name:" or "CHARACTER NAME:"
      const match = line.match(/^([A-Z][a-zA-Z\s]+):/);
      if (match) {
        characterNames.add(match[1].trim());
      }
    });

    return Array.from(characterNames).map((name) => ({
      name,
      description: `Character ${name} from the script`,
      mode: 'generate',
      imageCount: 3,
      generatedImages: [],
      selectedImage: null,
    }));
  }

  const handleGenerateImages = async (characterName: string) => {
    const character = characters.find((c) => c.name === characterName);
    if (!character) return;

    logger.info('Step2CharacterImages', `Generating images for character: ${characterName}`, {
      count: character.imageCount,
    });

    setGeneratingFor(characterName);
    setError(null);

    try {
      const imagePromises = Array.from({ length: character.imageCount }).map(() =>
        apiClient.generateImage({
          prompt: `Character reference sheet, ${character.description}, multiple angles, consistent style, professional character design`,
          service: 'doubao',
          width: 1024,
          height: 1024,
          optimize_prompt: true,
        })
      );

      const results = await Promise.all(imagePromises);
      const imageUrls = results.map((r) => r.image_url);

      setCharacters((prev) =>
        prev.map((c) =>
          c.name === characterName
            ? { ...c, generatedImages: imageUrls, selectedImage: imageUrls[0] }
            : c
        )
      );

      logger.info('Step2CharacterImages', `Generated ${imageUrls.length} images for ${characterName}`);
    } catch (err) {
      logger.error('Step2CharacterImages', `Failed to generate images for ${characterName}`, err);
      
      if (err instanceof APIException) {
        setError(`Failed to generate images: ${err.message}`);
      } else {
        setError('An unexpected error occurred. Please try again.');
      }
    } finally {
      setGeneratingFor(null);
    }
  };

  const handleImageSelect = (characterName: string, imageUrl: string) => {
    setCharacters((prev) =>
      prev.map((c) =>
        c.name === characterName ? { ...c, selectedImage: imageUrl } : c
      )
    );
    logger.debug('Step2CharacterImages', `Selected image for ${characterName}`);
  };

  const handleFileUpload = async (characterName: string, file: File) => {
    logger.info('Step2CharacterImages', `Uploading image for ${characterName}`);

    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      setCharacters((prev) =>
        prev.map((c) =>
          c.name === characterName
            ? {
                ...c,
                generatedImages: [dataUrl, ...c.generatedImages],
                selectedImage: dataUrl,
              }
            : c
        )
      );
    };
    reader.readAsDataURL(file);
  };

  const handleNext = () => {
    const missingCharacters = characters.filter((c) => !c.selectedImage);
    
    if (missingCharacters.length > 0) {
      setError(
        `Please select or generate images for: ${missingCharacters.map((c) => c.name).join(', ')}`
      );
      return;
    }

    logger.info('Step2CharacterImages', 'Proceeding to scene images step');
    onNext(characters);
  };

  return (
    <div className="space-y-6">
      <Card>
        <p className="text-apple-body text-text-secondary">
          For each character, you can either generate reference images using AI or upload your
          own. Select the best image for each character to ensure consistency throughout the
          video.
        </p>
      </Card>

      {/* Character Cards */}
      <div className="space-y-6">
        {characters.map((character) => (
          <Card key={character.name} title={character.name}>
            <div className="space-y-4">
              {/* Mode Selection */}
              <div className="flex gap-4">
                <Button
                  variant={character.mode === 'generate' ? 'primary' : 'secondary'}
                  size="sm"
                  onClick={() =>
                    setCharacters((prev) =>
                      prev.map((c) =>
                        c.name === character.name ? { ...c, mode: 'generate' } : c
                      )
                    )
                  }
                >
                  Auto Generate
                </Button>
                <Button
                  variant={character.mode === 'upload' ? 'primary' : 'secondary'}
                  size="sm"
                  onClick={() =>
                    setCharacters((prev) =>
                      prev.map((c) =>
                        c.name === character.name ? { ...c, mode: 'upload' } : c
                      )
                    )
                  }
                >
                  Manual Upload
                </Button>
              </div>

              {/* Generate Mode */}
              {character.mode === 'generate' && (
                <div className="flex gap-4 items-end">
                  <Input
                    label="Number of Images"
                    type="number"
                    min="1"
                    max="5"
                    value={character.imageCount}
                    onChange={(e) =>
                      setCharacters((prev) =>
                        prev.map((c) =>
                          c.name === character.name
                            ? { ...c, imageCount: parseInt(e.target.value, 10) }
                            : c
                        )
                      )
                    }
                    className="w-32"
                  />
                  <Button
                    onClick={() => handleGenerateImages(character.name)}
                    loading={generatingFor === character.name}
                    disabled={generatingFor !== null}
                  >
                    Generate Images
                  </Button>
                </div>
              )}

              {/* Upload Mode */}
              {character.mode === 'upload' && (
                <div>
                  <Input
                    type="file"
                    accept="image/*"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) {
                        handleFileUpload(character.name, file);
                      }
                    }}
                  />
                </div>
              )}

              {/* Loading State */}
              {generatingFor === character.name && (
                <LoadingAnimation message="Generating character images..." />
              )}

              {/* Image Grid */}
              {character.generatedImages.length > 0 && (
                <ImageGrid
                  images={character.generatedImages.map((url) => ({
                    id: url,
                    url,
                    selected: url === character.selectedImage,
                  }))}
                  onSelect={(imageUrl) => handleImageSelect(character.name, imageUrl)}
                  columns={3}
                  aspectRatio="1/1"
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
          Next: Scene Images →
        </Button>
      </div>
    </div>
  );
};

export default Step2CharacterImages;

