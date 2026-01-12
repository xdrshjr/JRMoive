'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Card, Button, ProgressBar, LogViewer, LoadingAnimation } from '@/components/ui';
import { apiClient } from '@/lib/api';
import { logger } from '@/lib/logger';
import { Scene, Character, LogEntry, TaskStatusResponse, APIException, QuickModeScene } from '@/lib/types';

interface Step4VideoProgressProps {
  polishedScript: string;
  characters: Character[];
  scenes: Scene[];
  onComplete: (videoUrl: string, metadata: any) => void;
  onCancel: () => void;
  quickModeScenes?: QuickModeScene[];
  isQuickMode?: boolean;
}

export const Step4VideoProgress: React.FC<Step4VideoProgressProps> = ({
  polishedScript,
  characters,
  scenes,
  onComplete,
  onCancel,
  quickModeScenes = [],
  isQuickMode = false,
}) => {
  const [taskId, setTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<string>('pending');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [currentStage, setCurrentStage] = useState('Initializing');
  const [error, setError] = useState<string | null>(null);
  
  // Use ref to prevent double execution in React StrictMode
  const hasStartedRef = useRef(false);

  const addLog = (level: LogEntry['level'], component: string, message: string, data?: any) => {
    const logEntry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      component,
      message,
      data,
    };
    setLogs((prev) => [...prev, logEntry]);
    logger[level]('Step4VideoProgress', message, data);
  };

  useEffect(() => {
    // Start video generation when component mounts (only once)
    // Use ref to prevent double execution in React 18 StrictMode
    if (!hasStartedRef.current) {
      hasStartedRef.current = true;
      if (isQuickMode) {
        startQuickModeGeneration();
      } else {
        startWorkflowGeneration();
      }
    }
  }, []); // Empty dependency array - only run on mount

  const startQuickModeGeneration = async () => {
    addLog('info', 'QuickModeGeneration', 'Starting quick mode video generation');

    try {
      // Prepare scenes for API
      const apiScenes = quickModeScenes.map((scene) => ({
        scene_id: scene.id,
        image: scene.imageBase64,
        duration: scene.duration,
        prompt: scene.prompt || undefined,
        camera_motion: scene.cameraMotion || undefined,
        motion_strength: scene.motionStrength,
      }));

      addLog('info', 'QuickModeGeneration',
        `Submitting ${apiScenes.length} scenes for video generation`
      );
      setCurrentStage('Submitting Quick Mode Workflow');

      // Call quick mode API
      const response = await apiClient.startQuickModeWorkflow({
        mode: 'quick',
        scenes: apiScenes,
        config: {
          video_fps: 30,
          video_resolution: '1920x1080',
          add_transitions: true,
        },
      });

      setTaskId(response.task_id);
      addLog('info', 'QuickModeGeneration', `Quick mode task submitted successfully, task_id: ${response.task_id}`);

      // Start polling
      pollTaskStatus(response.task_id, true);
    } catch (err) {
      addLog('error', 'QuickModeGeneration', 'Failed to start quick mode generation', err);

      if (err instanceof APIException) {
        setError(`Failed to start quick mode: ${err.message}`);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred');
      }
      setStatus('failed');
    }
  };

  const startWorkflowGeneration = async () => {
    addLog('info', 'WorkflowGeneration', 'Starting full workflow generation pipeline');
    
    try {
      // Clean the script - remove markdown code blocks if present
      let cleanedScript = polishedScript.trim();
      const codeBlockMatch = cleanedScript.match(/^```(?:yaml|yml)?\s*\n([\s\S]*?)\n```$/);
      if (codeBlockMatch) {
        cleanedScript = codeBlockMatch[1].trim();
        addLog('debug', 'WorkflowGeneration', 'Stripped markdown code blocks from script');
      }

      // Prepare character images mapping
      const characterImages: Record<string, string> = {};
      for (const char of characters) {
        if (char.selectedImage) {
          characterImages[char.name] = char.selectedImage;
          addLog('debug', 'WorkflowGeneration', `Using character image for ${char.name}`);
        }
      }

      // Prepare scene images mapping
      const sceneImages: Record<string, string> = {};
      for (const scene of scenes) {
        if (scene.selectedImage) {
          sceneImages[scene.id] = scene.selectedImage;
          addLog('debug', 'WorkflowGeneration', `Using scene image for ${scene.id}`);
        }
      }

      addLog('info', 'WorkflowGeneration', 
        `Starting workflow with ${Object.keys(characterImages).length} character images and ${Object.keys(sceneImages).length} scene images`
      );
      setCurrentStage('Submitting Workflow');

      // Call workflow API with cleaned script
      const response = await apiClient.startWorkflow({
        script: cleanedScript,
        characterImages: Object.keys(characterImages).length > 0 ? characterImages : undefined,
        sceneImages: Object.keys(sceneImages).length > 0 ? sceneImages : undefined,
        config: {
          video_fps: 30,
          video_duration: 5.0,
          image_width: 1920,
          image_height: 1080,
          add_transitions: true,
          add_subtitles: false,
          enable_character_references: true,
          video_motion_strength: 0.5,
          max_concurrent_requests: 3,
        },
      });

      setTaskId(response.task_id);
      addLog('info', 'WorkflowGeneration', `Workflow task submitted successfully, task_id: ${response.task_id}`);

      // Start polling
      pollTaskStatus(response.task_id, false);
    } catch (err) {
      addLog('error', 'WorkflowGeneration', 'Failed to start workflow generation', err);
      
      if (err instanceof APIException) {
        setError(`Failed to start workflow: ${err.message}`);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred');
      }
      setStatus('failed');
    }
  };

  const pollTaskStatus = async (taskId: string, isQuickMode: boolean = false) => {
    try {
      await apiClient.pollTaskUntilComplete(
        taskId,
        (statusUpdate: TaskStatusResponse) => {
          setProgress(statusUpdate.progress);
          setStatus(statusUpdate.status);

          // Update stage based on progress and mode
          if (isQuickMode) {
            // Quick mode stages
            if (statusUpdate.progress < 10) {
              setCurrentStage('Preparing Images');
            } else if (statusUpdate.progress < 70) {
              setCurrentStage('Generating Videos from Images');
            } else if (statusUpdate.progress < 95) {
              setCurrentStage('Composing Final Video');
            } else {
              setCurrentStage('Finalizing');
            }
          } else {
            // Full mode stages
            if (statusUpdate.progress < 10) {
              setCurrentStage('Initializing Project');
            } else if (statusUpdate.progress < 20) {
              setCurrentStage('Parsing Script');
            } else if (statusUpdate.progress < 40) {
              setCurrentStage('Processing Character References');
            } else if (statusUpdate.progress < 60) {
              setCurrentStage('Generating Scene Images');
            } else if (statusUpdate.progress < 85) {
              setCurrentStage('Generating Scene Videos');
            } else if (statusUpdate.progress < 98) {
              setCurrentStage('Composing Final Video');
            } else {
              setCurrentStage('Finalizing');
            }
          }

          addLog(
            'info',
            'WorkflowGeneration',
            `Progress: ${statusUpdate.progress}% - ${currentStage}`
          );
        },
        14400000 // 4 hours max (for very long video generation)
      );

      // Get final result
      const finalStatus = await apiClient.getTaskStatus(taskId);
      
      if (finalStatus.status === 'completed' && finalStatus.result) {
        const workflowResult = finalStatus.result;
        
        addLog('info', 'WorkflowGeneration', 'Workflow completed successfully', {
          videoUrl: workflowResult.video_url,
          duration: workflowResult.duration,
          sceneCount: workflowResult.scene_count,
          characterCount: workflowResult.character_count,
        });
        
        // Pass result to parent
        onComplete(workflowResult.video_url, {
          duration: workflowResult.duration,
          sceneCount: workflowResult.scene_count,
          characterCount: workflowResult.character_count,
          assets: workflowResult.assets,
        });
      } else {
        throw new Error('Workflow completed but no result found');
      }
    } catch (err) {
      addLog('error', 'WorkflowGeneration', 'Workflow generation failed', err);
      
      if (err instanceof APIException) {
        setError(`Workflow failed: ${err.message}`);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred');
      }
      setStatus('failed');
    }
  };

  const handleCancel = async () => {
    if (taskId) {
      addLog('warn', 'WorkflowGeneration', 'User requested cancellation');
      
      try {
        await apiClient.cancelTask(taskId);
        addLog('info', 'WorkflowGeneration', 'Task cancelled successfully');
        setStatus('cancelled');
        onCancel();
      } catch (err) {
        addLog('error', 'WorkflowGeneration', 'Failed to cancel task', err);
      }
    } else {
      onCancel();
    }
  };

  // Stage indicators
  const stages = [
    'Initializing',
    'Parsing Script',
    'Character References',
    'Scene Images',
    'Scene Videos',
    'Composing Video',
    'Finalizing',
  ];

  return (
    <div className="space-y-6">
      {/* Progress Section */}
      <Card title="Video Generation Progress">
        <div className="space-y-6">
          {/* Progress Bar */}
          <ProgressBar
            progress={progress}
            label="Overall Progress"
            showPercentage={true}
            color={error ? 'red' : status === 'completed' ? 'green' : 'blue'}
          />

          {/* Current Stage */}
          <div className="text-center">
            <p className="text-apple-body text-text-secondary mb-2">Current Stage:</p>
            <p className="text-apple-headline text-text-primary font-semibold">{currentStage}</p>
          </div>

          {/* Status Message */}
          <div className="text-center">
            {status === 'processing' && (
              <LoadingAnimation message={`${currentStage}...`} />
            )}
            {status === 'completed' && (
              <p className="text-apple-green text-apple-headline">
                ✓ Video generation completed!
              </p>
            )}
            {status === 'failed' && error && (
              <p className="text-apple-red text-apple-headline">
                ✗ Generation failed
              </p>
            )}
          </div>

          {/* Cancel Button */}
          {(status === 'pending' || status === 'processing') && (
            <div className="flex justify-center">
              <Button variant="danger" onClick={handleCancel}>
                Cancel Generation
              </Button>
            </div>
          )}
        </div>
      </Card>

      {/* Logs Section */}
      <Card title="Generation Logs">
        <LogViewer logs={logs} maxHeight="500px" autoScroll={true} />
      </Card>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-apple-red rounded-apple-md p-4">
          <h4 className="text-apple-red font-semibold mb-2">Error</h4>
          <p className="text-apple-red text-sm">{error}</p>
          <div className="mt-4">
            <Button variant="secondary" onClick={onCancel}>
              Go Back
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Step4VideoProgress;
