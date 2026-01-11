'use client';

import React, { useState } from 'react';
import { Card, Button, Textarea } from '@/components/ui';
import { apiClient } from '@/lib/api';
import { logger } from '@/lib/logger';
import { APIException } from '@/lib/types';

interface Step1ScriptInputProps {
  onNext: (userScript: string, polishedScript: string) => void;
  initialUserScript?: string;
  initialPolishedScript?: string;
}

export const Step1ScriptInput: React.FC<Step1ScriptInputProps> = ({
  onNext,
  initialUserScript = '',
  initialPolishedScript = '',
}) => {
  const [userScript, setUserScript] = useState(initialUserScript);
  const [polishedScript, setPolishedScript] = useState(initialPolishedScript);
  const [isPolishing, setIsPolishing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handlePolish = async () => {
    if (!userScript.trim()) {
      setError('Please enter a script description');
      return;
    }

    logger.info('Step1ScriptInput', 'User submitted script for polishing');
    setIsPolishing(true);
    setError(null);

    try {
      const response = await apiClient.chat({
        messages: [
          {
            role: 'system',
            content:
              'You are a professional screenwriter. Polish the following script into standard screenplay format with clear scenes, dialogues, and stage directions. Use markdown formatting with ## for scene headers.',
          },
          {
            role: 'user',
            content: userScript,
          },
        ],
        temperature: 0.7,
      });

      const polished = response.choices[0]?.message?.content || '';
      setPolishedScript(polished);
      logger.info('Step1ScriptInput', 'Script polished successfully', {
        originalLength: userScript.length,
        polishedLength: polished.length,
      });
    } catch (err) {
      logger.error('Step1ScriptInput', 'Failed to polish script', err);
      
      if (err instanceof APIException) {
        setError(`Failed to polish script: ${err.message}`);
      } else {
        setError('An unexpected error occurred. Please try again.');
      }
    } finally {
      setIsPolishing(false);
    }
  };

  const handleNext = () => {
    if (!polishedScript.trim()) {
      setError('Please polish the script first or enter a polished version manually');
      return;
    }

    logger.info('Step1ScriptInput', 'User proceeding to next step');
    onNext(userScript, polishedScript);
  };

  return (
    <div className="space-y-6">
      {/* User Input Section */}
      <Card title="Enter Your Script Description">
        <Textarea
          label="Script Description"
          placeholder="Enter your script idea here... For example: A programmer's day - Starting in the morning at the office, working on code, having lunch with colleagues, and finally finishing a project in the evening."
          value={userScript}
          onChange={(e) => setUserScript(e.target.value)}
          rows={8}
          helperText="Provide a brief description or outline of your video script. The AI will help polish it into a proper screenplay format."
        />
        <div className="mt-4">
          <Button
            onClick={handlePolish}
            loading={isPolishing}
            disabled={!userScript.trim() || isPolishing}
          >
            {isPolishing ? 'Polishing Script...' : 'Polish Script'}
          </Button>
        </div>
      </Card>

      {/* Polished Script Section */}
      {polishedScript && (
        <Card title="Polished Script" subtitle="You can edit this script before proceeding">
          <Textarea
            label="Polished Screenplay"
            value={polishedScript}
            onChange={(e) => setPolishedScript(e.target.value)}
            rows={12}
            helperText="Edit the polished script as needed. This will be used to generate character and scene images."
          />
        </Card>
      )}

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-apple-red rounded-apple-md p-4">
          <p className="text-apple-red text-sm">{error}</p>
        </div>
      )}

      {/* Next Button */}
      <div className="flex justify-end">
        <Button
          onClick={handleNext}
          disabled={!polishedScript.trim()}
          size="lg"
        >
          Next: Character Images →
        </Button>
      </div>
    </div>
  );
};

export default Step1ScriptInput;

