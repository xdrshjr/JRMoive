import React from 'react';
import Image from 'next/image';
import { isValidImageUrl } from '@/lib/imageHelpers';

interface ImageOption {
  id: string;
  url: string;
  selected: boolean;
}

interface ImageGridProps {
  images: ImageOption[];
  onSelect: (id: string) => void;
  columns?: number;
  aspectRatio?: string;
}

export const ImageGrid: React.FC<ImageGridProps> = ({
  images,
  onSelect,
  columns = 3,
  aspectRatio = '16/9',
}) => {
  const gridClasses = {
    2: 'grid-cols-2',
    3: 'grid-cols-3',
    4: 'grid-cols-4',
  }[columns] || 'grid-cols-3';

  // Filter out any invalid images
  const validImages = images.filter((img) => isValidImageUrl(img.url));

  if (validImages.length === 0) {
    return (
      <div className="p-4 text-center text-text-secondary border border-text-tertiary rounded-apple-md">
        <p>No valid images to display</p>
      </div>
    );
  }

  return (
    <div className={`grid ${gridClasses} gap-4`}>
      {validImages.map((image) => (
        <div
          key={image.id}
          onClick={() => onSelect(image.id)}
          className={`relative cursor-pointer rounded-apple-md overflow-hidden transition-apple ${
            image.selected
              ? 'ring-4 ring-apple-blue shadow-apple-lg'
              : 'ring-1 ring-text-tertiary hover:ring-2 hover:ring-apple-blue'
          }`}
          style={{ aspectRatio }}
        >
          <Image
            src={image.url}
            alt={`Image ${image.id}`}
            fill
            className="object-cover"
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
            unoptimized={image.url.startsWith('data:')}
          />
          {image.selected && (
            <div className="absolute top-2 right-2 bg-apple-blue text-white rounded-full w-8 h-8 flex items-center justify-center">
              <svg
                className="w-5 h-5"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

export default ImageGrid;

