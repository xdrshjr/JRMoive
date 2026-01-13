/**
 * Step 0: Video Type Selection
 *
 * Allows users to select the video type and subtype before script generation.
 * This selection affects script generation, image prompts, and video generation.
 */

import React, { useState } from 'react';
import {
  VideoType,
  VideoSubtype,
  VIDEO_TYPE_DEFINITIONS,
  getVideoTypeDisplayName,
  getSubtypeDisplayName,
  getSubtypeDescription,
} from '@/lib/types/videoTypes';

interface Step0VideoTypeSelectionProps {
  onNext: (videoType: VideoType, videoSubtype: VideoSubtype) => void;
  initialVideoType?: VideoType;
  initialVideoSubtype?: VideoSubtype;
}

export default function Step0VideoTypeSelection({
  onNext,
  initialVideoType,
  initialVideoSubtype,
}: Step0VideoTypeSelectionProps) {
  const [selectedType, setSelectedType] = useState<VideoType | null>(
    initialVideoType || null
  );
  const [selectedSubtype, setSelectedSubtype] = useState<string | null>(
    initialVideoSubtype || null
  );

  const handleTypeSelect = (type: VideoType) => {
    setSelectedType(type);
    setSelectedSubtype(null); // Reset subtype when type changes
  };

  const handleSubtypeSelect = (subtype: string) => {
    setSelectedSubtype(subtype);
  };

  const handleContinue = () => {
    if (selectedType && selectedSubtype) {
      onNext(selectedType, selectedSubtype as VideoSubtype);
    }
  };

  const isValid = selectedType && selectedSubtype;

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-8">
      {/* Header */}
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          选择视频类型
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          选择您想要生成的视频类型和风格，这将影响剧本生成和视觉效果
        </p>
      </div>

      {/* Video Type Selection */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-200">
          1. 选择视频类型
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {(Object.keys(VIDEO_TYPE_DEFINITIONS) as VideoType[]).map((type) => {
            const def = VIDEO_TYPE_DEFINITIONS[type];
            const isSelected = selectedType === type;

            return (
              <button
                key={type}
                onClick={() => handleTypeSelect(type)}
                className={`
                  relative p-6 rounded-lg border-2 transition-all duration-200
                  hover:shadow-lg hover:scale-105
                  ${
                    isSelected
                      ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 shadow-md'
                      : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-blue-300'
                  }
                `}
              >
                {/* Icon */}
                <div className="text-4xl mb-3">{def.icon}</div>

                {/* Name */}
                <div className="font-semibold text-lg text-gray-900 dark:text-white mb-2">
                  {def.name_zh}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                  {def.name_en}
                </div>

                {/* Description */}
                <div className="text-sm text-gray-600 dark:text-gray-300">
                  {def.description_zh}
                </div>

                {/* Selected indicator */}
                {isSelected && (
                  <div className="absolute top-3 right-3">
                    <div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                      <svg
                        className="w-4 h-4 text-white"
                        fill="none"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path d="M5 13l4 4L19 7"></path>
                      </svg>
                    </div>
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Subtype Selection */}
      {selectedType && (
        <div className="space-y-4 animate-fadeIn">
          <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-200">
            2. 选择子类型 ({getVideoTypeDisplayName(selectedType, 'zh')})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.keys(VIDEO_TYPE_DEFINITIONS[selectedType].subtypes).map(
              (subtype) => {
                const subtypeDef =
                  VIDEO_TYPE_DEFINITIONS[selectedType].subtypes[subtype];
                const isSelected = selectedSubtype === subtype;

                return (
                  <button
                    key={subtype}
                    onClick={() => handleSubtypeSelect(subtype)}
                    className={`
                      relative p-5 rounded-lg border-2 text-left transition-all duration-200
                      hover:shadow-md
                      ${
                        isSelected
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 shadow-sm'
                          : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-blue-300'
                      }
                    `}
                  >
                    {/* Radio button */}
                    <div className="flex items-start space-x-3">
                      <div className="flex-shrink-0 mt-1">
                        <div
                          className={`
                          w-5 h-5 rounded-full border-2 flex items-center justify-center
                          ${
                            isSelected
                              ? 'border-blue-500 bg-blue-500'
                              : 'border-gray-300 dark:border-gray-600'
                          }
                        `}
                        >
                          {isSelected && (
                            <div className="w-2 h-2 bg-white rounded-full"></div>
                          )}
                        </div>
                      </div>

                      <div className="flex-1 min-w-0">
                        {/* Name */}
                        <div className="font-semibold text-gray-900 dark:text-white mb-1">
                          {subtypeDef.name_zh}
                          <span className="text-sm text-gray-500 dark:text-gray-400 ml-2">
                            ({subtypeDef.name_en})
                          </span>
                        </div>

                        {/* Description */}
                        <div className="text-sm text-gray-600 dark:text-gray-300 mb-2">
                          {subtypeDef.description_zh}
                        </div>

                        {/* Style keywords */}
                        <div className="flex flex-wrap gap-1">
                          {subtypeDef.styleKeywords.slice(0, 3).map((keyword) => (
                            <span
                              key={keyword}
                              className="inline-block px-2 py-0.5 text-xs rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300"
                            >
                              {keyword}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </button>
                );
              }
            )}
          </div>
        </div>
      )}

      {/* Continue Button */}
      <div className="flex justify-end pt-6 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={handleContinue}
          disabled={!isValid}
          className={`
            px-8 py-3 rounded-lg font-semibold text-white transition-all duration-200
            ${
              isValid
                ? 'bg-blue-600 hover:bg-blue-700 hover:shadow-lg'
                : 'bg-gray-300 dark:bg-gray-700 cursor-not-allowed'
            }
          `}
        >
          继续到剧本输入 →
        </button>
      </div>

      {/* Helper text */}
      {!selectedType && (
        <div className="text-center text-sm text-gray-500 dark:text-gray-400">
          请先选择一个视频类型
        </div>
      )}
      {selectedType && !selectedSubtype && (
        <div className="text-center text-sm text-gray-500 dark:text-gray-400">
          请选择一个子类型以继续
        </div>
      )}
    </div>
  );
}
