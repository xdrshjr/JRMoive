'use client';

import React, { useState, useEffect } from 'react';
import { Card, Button, ProgressBar, LogViewer, LoadingAnimation } from '@/components/ui';
import { apiClient } from '@/lib/api';
import { logger } from '@/lib/logger';
import { Scene, LogEntry, TaskStatusResponse, APIException } from '@/lib/types';

interface Step4VideoProgressProps {
  scenes: Scene[];
  onComplete: (videoUrl: string, metadata: any) => void;
  onCancel: () => void;
}

export const Step4VideoProgress: React.FC<Step4VideoProgressProps> = ({
  scenes,
  onComplete,
  onCancel,
}) => {
  const [taskId, setTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<string>('pending');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [currentStage, setCurrentStage] = useState('Initializing');
  const [error, setError] = useState<string | null>(null);

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
    // Start video generation when component mounts
    startVideoGeneration();
  }, []);

  const startVideoGeneration = async () => {
    addLog('info', 'VideoGeneration', 'Starting video generation workflow');
    
    /**
     * TODO: Backend - Create /api/v1/workflow/generate endpoint
     * This should orchestrate the full pipeline. For now, we generate videos
     * for each scene individually.
     */
    
    try {
      // For demonstration, generate video for the first scene
      // In production, this would call a workflow orchestration API
      const firstScene = scenes[0];
      
      if (!firstScene || !firstScene.selectedImage) {
        throw new Error('No scene image selected');
      }

      addLog('info', 'VideoGeneration', `Generating video for ${firstScene.id}`);
      setCurrentStage('Generating Video');

      // Convert image URL to base64 if needed (simplified for demo)
      const imageData = firstScene.selectedImage;

      const response = await apiClient.generateVideo({
        image: imageData,
        prompt: `${firstScene.location}, ${firstScene.time}, ${firstScene.description}, cinematic camera movement`,
        duration: 5,
        fps: 30,
      });

      setTaskId(response.task_id);
      addLog('info', 'VideoGeneration', `Video generation started, task_id: ${response.task_id}`);

      // Start polling
      pollTaskStatus(response.task_id);
    } catch (err) {
      addLog('error', 'VideoGeneration', 'Failed to start video generation', err);
      
      if (err instanceof APIException) {
        setError(`Failed to start video generation: ${err.message}`);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred');
      }
      setStatus('failed');
    }
  };

  const pollTaskStatus = async (taskId: string) => {
    try {
      await apiClient.pollTaskUntilComplete(
        taskId,
        (statusUpdate: TaskStatusResponse) => {
          setProgress(statusUpdate.progress);
          setStatus(statusUpdate.status);
          
          // Update stage based on progress
          if (statusUpdate.progress < 20) {
            setCurrentStage('Initializing');
          } else if (statusUpdate.progress < 50) {
            setCurrentStage('Processing Video');
          } else if (statusUpdate.progress < 80) {
            setCurrentStage('Rendering');
          } else {
            setCurrentStage('Finalizing');
          }

          addLog(
            'info',
            'VideoGeneration',
            `Progress update: ${statusUpdate.progress}% - ${statusUpdate.status}`
          );
        }
      );

      // Get final result
      const finalStatus = await apiClient.getTaskStatus(taskId);
      
      if (finalStatus.status === 'completed' && finalStatus.result?.result?.video_url) {
        addLog('info', 'VideoGeneration', 'Video generation completed successfully');
        onComplete(finalStatus.result.result.video_url, {
          duration: finalStatus.result.duration,
        });
      } else {
        throw new Error('Video generation completed but no video URL found');
      }
    } catch (err) {
      addLog('error', 'VideoGeneration', 'Video generation failed', err);
      
      if (err instanceof APIException) {
        setError(`Video generation failed: ${err.message}`);
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
      addLog('warn', 'VideoGeneration', 'User requested cancellation');
      
      try {
        await apiClient.cancelTask(taskId);
        addLog('info', 'VideoGeneration', 'Task cancelled successfully');
        setStatus('cancelled');
        onCancel();
      } catch (err) {
        addLog('error', 'VideoGeneration', 'Failed to cancel task', err);
      }
    } else {
      onCancel();
    }
  };

  // Stage indicators
  const stages = [
    'Initializing',
    'Processing Video',
    'Rendering',
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

          {/* Stage Indicators */}
          <div className="flex justify-between">
            {stages.map((stage, index) => {
              const isActive = stage === currentStage;
              const isPast = stages.indexOf(currentStage) > index;
              
              return (
                <div
                  key={stage}
                  className={`flex-1 text-center pb-2 border-b-4 transition-apple ${
                    isActive
                      ? 'border-apple-blue text-apple-blue font-semibold'
                      : isPast
                      ? 'border-apple-green text-apple-green'
                      : 'border-text-tertiary text-text-secondary'
                  }`}
                >
                  <p className="text-apple-footnote">{stage}</p>
                </div>
              );
            })}
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

