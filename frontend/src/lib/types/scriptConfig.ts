/**
 * Script Generation Configuration Types
 *
 * Defines the configuration options available to users when generating scripts
 */

import { VideoType, VideoSubtype } from './videoTypes';

export type DramaGenre =
  | 'shuang_ju'      // 爽剧 (Power Fantasy)
  | 'comedy'         // 搞笑剧 (Comedy)
  | 'romance'        // 爱情剧 (Romance)
  | 'suspense'       // 悬疑剧 (Suspense)
  | 'action'         // 动作剧 (Action)
  | 'slice_of_life'  // 生活剧 (Slice of Life)
  | 'fantasy'        // 奇幻剧 (Fantasy)
  | 'horror'         // 恐怖剧 (Horror)
  | 'sci_fi'         // 科幻剧 (Sci-Fi)
  | 'other';         // 其他 (Other)

export interface ScriptGenerationConfig {
  // Video type settings (NEW)
  videoType?: VideoType;                // 视频类型
  videoSubtype?: VideoSubtype;          // 视频子类型

  // Character settings
  characterCount: number;           // 人物个数 (1-10)

  // Genre settings
  genre: DramaGenre;                // 剧情种类
  genreCustom?: string;             // 自定义剧情类型 (when genre is 'other')

  // Content safety settings
  noPublicFigures: boolean;         // 不出现公众人物 (default: true)
  noMinors: boolean;                // 不出现未成年 (default: true)
  noViolence: boolean;              // 不出现暴力内容 (default: false)
  noSensitiveTopics: boolean;       // 不出现敏感话题 (default: false)

  // Scene settings
  sceneCount: number;               // 场景数 (1-20, default: 3)
  subSceneCount: number;            // 每个场景的子场景数 (0-5, default: 0)

  // Optional advanced settings
  targetAudience?: 'general' | 'youth' | 'adult';  // 目标受众
  pacing?: 'slow' | 'medium' | 'fast';             // 节奏
  tone?: 'serious' | 'lighthearted' | 'dramatic';  // 基调
}

export const DEFAULT_SCRIPT_CONFIG: ScriptGenerationConfig = {
  characterCount: 2,
  genre: 'slice_of_life',
  noPublicFigures: true,
  noMinors: true,
  noViolence: false,
  noSensitiveTopics: false,
  sceneCount: 3,
  subSceneCount: 0,
  targetAudience: 'general',
  pacing: 'medium',
  tone: 'lighthearted',
};

export const GENRE_LABELS: Record<DramaGenre, { zh: string; en: string; description: string }> = {
  shuang_ju: {
    zh: '爽剧',
    en: 'Power Fantasy',
    description: '主角一路开挂，逆袭成功的故事',
  },
  comedy: {
    zh: '搞笑剧',
    en: 'Comedy',
    description: '轻松幽默，让人捧腹大笑',
  },
  romance: {
    zh: '爱情剧',
    en: 'Romance',
    description: '浪漫温馨的爱情故事',
  },
  suspense: {
    zh: '悬疑剧',
    en: 'Suspense',
    description: '扣人心弦的悬疑推理',
  },
  action: {
    zh: '动作剧',
    en: 'Action',
    description: '激烈刺激的动作场面',
  },
  slice_of_life: {
    zh: '生活剧',
    en: 'Slice of Life',
    description: '贴近生活的日常故事',
  },
  fantasy: {
    zh: '奇幻剧',
    en: 'Fantasy',
    description: '充满魔法与想象的奇幻世界',
  },
  horror: {
    zh: '恐怖剧',
    en: 'Horror',
    description: '惊悚恐怖的氛围营造',
  },
  sci_fi: {
    zh: '科幻剧',
    en: 'Sci-Fi',
    description: '未来科技与想象的结合',
  },
  other: {
    zh: '其他',
    en: 'Other',
    description: '自定义剧情类型',
  },
};

/**
 * Validates script generation configuration
 */
export function validateScriptConfig(config: ScriptGenerationConfig): {
  isValid: boolean;
  errors: string[];
} {
  const errors: string[] = [];

  if (config.characterCount < 1 || config.characterCount > 10) {
    errors.push('Character count must be between 1 and 10');
  }

  if (config.sceneCount < 1 || config.sceneCount > 20) {
    errors.push('Scene count must be between 1 and 20');
  }

  if (config.subSceneCount < 0 || config.subSceneCount > 5) {
    errors.push('Sub-scene count must be between 0 and 5');
  }

  if (config.genre === 'other' && !config.genreCustom?.trim()) {
    errors.push('Custom genre description is required when genre is "Other"');
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}
