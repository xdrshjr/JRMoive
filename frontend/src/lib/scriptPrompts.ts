/**
 * Script Generation Prompts for YAML Format
 *
 * These prompts enforce strict YAML format compliance for script generation
 * to ensure proper parsing by the backend ScriptParserAgent.
 */

import { ScriptGenerationConfig, GENRE_LABELS } from './types/scriptConfig';

/**
 * Detects if the input text is primarily in Chinese
 */
export function detectLanguage(text: string): 'zh' | 'en' {
  // Count Chinese characters
  const chineseChars = (text.match(/[\u4e00-\u9fff]/g) || []).length;
  // Count English words
  const englishWords = (text.match(/\b[a-zA-Z]+\b/g) || []).length;

  return chineseChars > englishWords ? 'zh' : 'en';
}

/**
 * Builds configuration constraints text for Chinese prompts
 */
function buildChineseConfigConstraints(config: ScriptGenerationConfig): string {
  const constraints: string[] = [];

  // Genre
  const genreLabel = config.genre === 'other' && config.genreCustom
    ? config.genreCustom
    : GENRE_LABELS[config.genre].zh;
  constraints.push(`- **剧情类型**: ${genreLabel}（${GENRE_LABELS[config.genre].description}）`);

  // Character count
  constraints.push(`- **角色数量**: 必须创建恰好 ${config.characterCount} 个主要角色`);

  // Scene count
  constraints.push(`- **场景数量**: 必须创建恰好 ${config.sceneCount} 个主场景`);

  // Sub-scenes
  if (config.subSceneCount > 0) {
    constraints.push(`- **子场景**: 每个主场景包含 ${config.subSceneCount} 个子场景`);
  }

  // Content safety
  const safetyRules: string[] = [];
  if (config.noPublicFigures) {
    safetyRules.push('不得出现真实公众人物的名字或形象');
  }
  if (config.noMinors) {
    safetyRules.push('所有角色必须是成年人（18岁以上）');
  }
  if (config.noViolence) {
    safetyRules.push('不得包含暴力、血腥场景');
  }
  if (config.noSensitiveTopics) {
    safetyRules.push('避免政治、宗教等敏感话题');
  }

  if (safetyRules.length > 0) {
    constraints.push(`- **内容安全规范**: ${safetyRules.join('；')}`);
  }

  // Advanced settings
  if (config.targetAudience) {
    const audienceMap = {
      general: '全年龄',
      youth: '青少年',
      adult: '成人'
    };
    constraints.push(`- **目标受众**: ${audienceMap[config.targetAudience]}`);
  }

  if (config.pacing) {
    const pacingMap = {
      slow: '慢节奏（细腻、舒缓）',
      medium: '中等节奏（平衡）',
      fast: '快节奏（紧凑、刺激）'
    };
    constraints.push(`- **剧情节奏**: ${pacingMap[config.pacing]}`);
  }

  if (config.tone) {
    const toneMap = {
      lighthearted: '轻松愉快',
      serious: '严肃认真',
      dramatic: '戏剧化、情感浓烈'
    };
    constraints.push(`- **整体基调**: ${toneMap[config.tone]}`);
  }

  return constraints.join('\n');
}

/**
 * Builds configuration constraints text for English prompts
 */
function buildEnglishConfigConstraints(config: ScriptGenerationConfig): string {
  const constraints: string[] = [];

  // Genre
  const genreLabel = config.genre === 'other' && config.genreCustom
    ? config.genreCustom
    : GENRE_LABELS[config.genre].en;
  constraints.push(`- **Genre**: ${genreLabel} (${GENRE_LABELS[config.genre].description})`);

  // Character count
  constraints.push(`- **Character Count**: Must create exactly ${config.characterCount} main character(s)`);

  // Scene count
  constraints.push(`- **Scene Count**: Must create exactly ${config.sceneCount} main scene(s)`);

  // Sub-scenes
  if (config.subSceneCount > 0) {
    constraints.push(`- **Sub-scenes**: Each main scene contains ${config.subSceneCount} sub-scene(s)`);
  }

  // Content safety
  const safetyRules: string[] = [];
  if (config.noPublicFigures) {
    safetyRules.push('no real public figures or their names');
  }
  if (config.noMinors) {
    safetyRules.push('all characters must be adults (18+)');
  }
  if (config.noViolence) {
    safetyRules.push('no violence or gore');
  }
  if (config.noSensitiveTopics) {
    safetyRules.push('avoid political or religious sensitive topics');
  }

  if (safetyRules.length > 0) {
    constraints.push(`- **Content Safety**: ${safetyRules.join('; ')}`);
  }

  // Advanced settings
  if (config.targetAudience) {
    const audienceMap = {
      general: 'General audience',
      youth: 'Youth',
      adult: 'Adult'
    };
    constraints.push(`- **Target Audience**: ${audienceMap[config.targetAudience]}`);
  }

  if (config.pacing) {
    const pacingMap = {
      slow: 'Slow (detailed, relaxed)',
      medium: 'Medium (balanced)',
      fast: 'Fast (compact, exciting)'
    };
    constraints.push(`- **Pacing**: ${pacingMap[config.pacing]}`);
  }

  if (config.tone) {
    const toneMap = {
      lighthearted: 'Lighthearted and cheerful',
      serious: 'Serious and earnest',
      dramatic: 'Dramatic with intense emotions'
    };
    constraints.push(`- **Tone**: ${toneMap[config.tone]}`);
  }

  return constraints.join('\n');
}

/**
 * Chinese system prompt for YAML script generation
 */
export const CHINESE_SYSTEM_PROMPT = `你是一位专业的剧本编剧，专门创作用于短视频生成的结构化剧本。

你必须严格按照YAML格式输出剧本，使用以下结构：

\`\`\`yaml
title: "剧本标题"
author: "作者名"
description: "剧本简介（一句话概括）"

characters:
  - name: "角色名"
    description: "角色描述（包含年龄、外貌、性格等）"
    age: 25
    gender: "male"
    appearance: "详细外貌描述"

scenes:
  - scene_id: "scene_001"
    location: "具体地点"
    time: "时间（如：清晨、中午、深夜）"
    weather: "天气状况"
    atmosphere: "氛围描述"
    description: "场景详细视觉描述"
    shot_type: "medium_shot"
    camera_movement: "static"
    duration: 8.0
    visual_style: "cinematic"
    color_tone: "warm"
    action: "角色动作描述"
    extract_frame_index: -5
    base_image_filename: null
    characters:
      - "角色1"
      - "角色2"
    dialogues:
      - character: "角色名"
        content: "台词内容"
        emotion: "情绪"
        voice_style: "语气"
    narrations:
      - content: "旁白内容"
        voice_style: "语气"
    sound_effects:
      - description: "音效描述"
        timing: 2.0
    sub_scenes: []
\`\`\`

**关键要求：**

1. **严格的YAML格式**：
   - 使用正确的缩进（2个空格）
   - 字符串值使用双引号包裹
   - 列表使用 \`-\` 开头
   - null值用小写的 null

2. **必填字段（每个场景）**：
   - scene_id: 格式为 "scene_001", "scene_002" 等
   - location: 具体地点描述
   - time: 时间
   - description: 详细的场景视觉描述
   - shot_type: 从以下选择
     * close_up (特写)
     * medium_shot (中景)
     * long_shot (远景)
     * full_shot (全景)
   - camera_movement: 从以下选择
     * static (静止)
     * pan (摇镜)
     * tilt (俯仰)
     * zoom (推拉)
     * dolly (移动)
     * tracking (跟踪)

3. **时长限制**：
   - 每个场景的duration必须在5-10秒之间
   - 最大不超过10秒（系统硬性限制）

4. **角色定义**：
   - 在characters列表中定义所有角色
   - 必须包含name和description
   - age, gender, appearance是可选的

5. **对话和旁白**：
   - dialogues和narrations都是列表
   - 空列表用 \`[]\` 表示

6. **可选字段**：
   - weather, atmosphere, action可以为null
   - visual_style, color_tone可以为null
   - sub_scenes默认为空列表

只输出符合上述格式的YAML剧本，不要添加任何其他说明或注释。`;

/**
 * English system prompt for YAML script generation
 */
export const ENGLISH_SYSTEM_PROMPT = `You are a professional screenwriter specializing in creating structured scripts for short video generation.

You MUST output scripts in strict YAML format using this structure:

\`\`\`yaml
title: "Script Title"
author: "Author Name"
description: "Brief description (one sentence)"

characters:
  - name: "Character Name"
    description: "Character description (age, appearance, personality)"
    age: 25
    gender: "male"
    appearance: "Detailed appearance description"

scenes:
  - scene_id: "scene_001"
    location: "Specific location"
    time: "Time of day (e.g., Morning, Noon, Late Night)"
    weather: "Weather condition"
    atmosphere: "Atmosphere description"
    description: "Detailed visual scene description"
    shot_type: "medium_shot"
    camera_movement: "static"
    duration: 8.0
    visual_style: "cinematic"
    color_tone: "warm"
    action: "Character action description"
    extract_frame_index: -5
    base_image_filename: null
    characters:
      - "Character1"
      - "Character2"
    dialogues:
      - character: "Character Name"
        content: "Dialogue content"
        emotion: "emotion"
        voice_style: "voice style"
    narrations:
      - content: "Narration content"
        voice_style: "voice style"
    sound_effects:
      - description: "Sound effect description"
        timing: 2.0
    sub_scenes: []
\`\`\`

**Critical Requirements:**

1. **Strict YAML Format**:
   - Use proper indentation (2 spaces)
   - Wrap string values in double quotes
   - Lists start with \`-\`
   - Use lowercase \`null\` for null values

2. **Required Fields (for each scene)**:
   - scene_id: Format as "scene_001", "scene_002", etc.
   - location: Specific location description
   - time: Time of day
   - description: Detailed visual scene description
   - shot_type: Choose from:
     * close_up
     * medium_shot
     * long_shot
     * full_shot
   - camera_movement: Choose from:
     * static
     * pan
     * tilt
     * zoom
     * dolly
     * tracking

3. **Duration Limits**:
   - Each scene's duration MUST be between 5-10 seconds
   - Maximum 10 seconds (system hard limit)

4. **Character Definitions**:
   - Define all characters in the characters list
   - Must include name and description
   - age, gender, appearance are optional

5. **Dialogues and Narrations**:
   - Both dialogues and narrations are lists
   - Empty lists should be \`[]\`

6. **Optional Fields**:
   - weather, atmosphere, action can be null
   - visual_style, color_tone can be null
   - sub_scenes defaults to empty list

Output ONLY the YAML script in the format above without any additional explanations or comments.`;

/**
 * Chinese user message template
 */
export const CHINESE_USER_MESSAGE = (userScript: string, config?: ScriptGenerationConfig) => {
  const configConstraints = config ? buildChineseConfigConstraints(config) : '';

  return `请将以下剧本创意转换为严格符合YAML格式的完整剧本：

${userScript}

${configConstraints ? `**用户配置要求：**\n${configConstraints}\n\n` : ''}要求：
1. 严格按照上述YAML格式输出
2. 补充所有必需字段
3. 确保场景编号连续（scene_001、scene_002、scene_003...）
4. 为每个场景添加合理的台词、旁白或音效（可以为空列表）
5. 场景描述要详细、具体、可视化
6. **重要：每个场景的duration必须在5-10秒之间，最大不超过10秒**
7. 使用正确的YAML语法（缩进、引号、列表格式）
8. 空列表用 [] 表示，空值用 null 表示
9. 所有字符串值都用双引号包裹
10. 如果用户没有指定角色，请创建合适的角色
${config ? `11. **严格遵守上述用户配置要求**，特别是角色数量、场景数量和内容安全规范` : ''}

开始输出YAML剧本：`;
};

/**
 * English user message template
 */
export const ENGLISH_USER_MESSAGE = (userScript: string, config?: ScriptGenerationConfig) => {
  const configConstraints = config ? buildEnglishConfigConstraints(config) : '';

  return `Please convert the following script idea into a complete script in strict YAML format:

${userScript}

${configConstraints ? `**User Configuration Requirements:**\n${configConstraints}\n\n` : ''}Requirements:
1. Strictly follow the YAML format specified above
2. Fill in all required fields
3. Ensure scene numbers are sequential (scene_001, scene_002, scene_003...)
4. Add appropriate dialogue, narration, or sound effects to each scene (can be empty lists)
5. Scene descriptions should be detailed, specific, and visual
6. **IMPORTANT: Each scene duration MUST be between 5-10 seconds, maximum 10 seconds**
7. Use correct YAML syntax (indentation, quotes, list formatting)
8. Empty lists should be [], empty values should be null
9. All string values should be wrapped in double quotes
10. If user didn't specify characters, create appropriate characters
${config ? `11. **Strictly follow the user configuration requirements above**, especially character count, scene count, and content safety rules` : ''}

Begin YAML script output:`;
};

/**
 * YAML format validation example in Chinese
 */
export const CHINESE_FORMAT_EXAMPLE = `
YAML格式示例：

\`\`\`yaml
title: "程序员的一天"
author: "AI编剧"
description: "讲述一个年轻程序员日常工作的温馨故事"

characters:
  - name: "小明"
    description: "25岁的Python开发者，戴黑框眼镜，清秀"
    age: 25
    gender: "male"
    appearance: "黑框眼镜，短发，白色T恤"

scenes:
  - scene_id: "scene_001"
    location: "温馨的咖啡馆"
    time: "清晨"
    weather: "晴朗"
    atmosphere: "温馨安静"
    description: "阳光透过大窗户洒进咖啡馆，小明坐在窗边的位置，手里拿着咖啡杯"
    shot_type: "medium_shot"
    camera_movement: "static"
    duration: 7.0
    visual_style: "cinematic"
    color_tone: "warm"
    action: "小明端起咖啡杯，满意地微笑"
    extract_frame_index: -5
    base_image_filename: null
    characters:
      - "小明"
    dialogues:
      - character: "小明"
        content: "今天又是充满希望的一天！"
        emotion: "微笑"
        voice_style: "温柔"
    narrations:
      - content: "这是小明工作的第三年，他依然保持着对编程的热情。"
        voice_style: "温暖"
    sound_effects:
      - description: "咖啡杯放在桌上的声音"
        timing: 2.0
    sub_scenes: []
\`\`\`
`;

/**
 * Get the appropriate prompts based on detected language
 */
export function getScriptPrompts(userScript: string, config?: ScriptGenerationConfig) {
  const language = detectLanguage(userScript);

  if (language === 'zh') {
    return {
      systemPrompt: CHINESE_SYSTEM_PROMPT,
      userMessage: CHINESE_USER_MESSAGE(userScript, config),
      formatExample: CHINESE_FORMAT_EXAMPLE,
      language: 'zh' as const,
    };
  } else {
    return {
      systemPrompt: ENGLISH_SYSTEM_PROMPT,
      userMessage: ENGLISH_USER_MESSAGE(userScript, config),
      formatExample: '',
      language: 'en' as const,
    };
  }
}
