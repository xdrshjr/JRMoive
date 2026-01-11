'use client';

import { useState } from 'react';
import Header from '@/components/Header';
import StepContainer from '@/components/StepContainer';
import Step1ScriptInput from '@/components/steps/Step1ScriptInput';
import Step2CharacterImages from '@/components/steps/Step2CharacterImages';
import Step3SceneImages from '@/components/steps/Step3SceneImages';
import Step4VideoProgress from '@/components/steps/Step4VideoProgress';
import Step5ResultPreview from '@/components/steps/Step5ResultPreview';
import { Character, Scene } from '@/lib/types';
import { logger } from '@/lib/logger';

export default function Home() {
  const [currentStep, setCurrentStep] = useState(1);
  
  // Step 1 state
  const [userScript, setUserScript] = useState('');
  const [polishedScript, setPolishedScript] = useState('');
  
  // Step 2 state
  const [characters, setCharacters] = useState<Character[]>([]);
  
  // Step 3 state
  const [scenes, setScenes] = useState<Scene[]>([]);
  
  // Step 5 state
  const [videoUrl, setVideoUrl] = useState('');
  const [videoMetadata, setVideoMetadata] = useState<any>(null);

  // Step 1: Script Input & Polish
  const handleStep1Complete = (userScriptText: string, polishedScriptText: string) => {
    logger.info('MainApp', 'Step 1 completed', { 
      userScriptLength: userScriptText.length,
      polishedScriptLength: polishedScriptText.length,
    });
    setUserScript(userScriptText);
    setPolishedScript(polishedScriptText);
    setCurrentStep(2);
  };

  // Step 2: Character Images
  const handleStep2Complete = (selectedCharacters: Character[]) => {
    logger.info('MainApp', 'Step 2 completed', { 
      characterCount: selectedCharacters.length,
    });
    setCharacters(selectedCharacters);
    setCurrentStep(3);
  };

  const handleStep2Back = () => {
    logger.info('MainApp', 'Returning to Step 1 from Step 2');
    setCurrentStep(1);
  };

  // Step 3: Scene Images
  const handleStep3Complete = (selectedScenes: Scene[]) => {
    logger.info('MainApp', 'Step 3 completed', { 
      sceneCount: selectedScenes.length,
    });
    setScenes(selectedScenes);
    setCurrentStep(4);
  };

  const handleStep3Back = () => {
    logger.info('MainApp', 'Returning to Step 2 from Step 3');
    setCurrentStep(2);
  };

  // Step 4: Video Generation Progress
  const handleStep4Complete = (generatedVideoUrl: string, metadata: any) => {
    logger.info('MainApp', 'Step 4 completed - video generation successful', {
      videoUrl: generatedVideoUrl,
      metadata,
    });
    setVideoUrl(generatedVideoUrl);
    setVideoMetadata(metadata);
    setCurrentStep(5);
  };

  const handleStep4Cancel = () => {
    logger.warn('MainApp', 'Video generation cancelled by user');
    setCurrentStep(3);
  };

  // Step 5: Result Preview
  const handleRegenerate = () => {
    logger.info('MainApp', 'User initiated regeneration - resetting to Step 1');
    // Reset all state
    setCurrentStep(1);
    setUserScript('');
    setPolishedScript('');
    setCharacters([]);
    setScenes([]);
    setVideoUrl('');
    setVideoMetadata(null);
  };

  return (
    <main className="min-h-screen bg-background">
      <Header />
      
      <StepContainer currentStep={currentStep} totalSteps={5}>
        {currentStep === 1 && (
          <Step1ScriptInput
            onNext={handleStep1Complete}
            initialUserScript={userScript}
            initialPolishedScript={polishedScript}
          />
        )}
        
        {currentStep === 2 && (
          <Step2CharacterImages
            polishedScript={polishedScript}
            onNext={handleStep2Complete}
            onBack={handleStep2Back}
            initialCharacters={characters}
          />
        )}
        
        {currentStep === 3 && (
          <Step3SceneImages
            polishedScript={polishedScript}
            onNext={handleStep3Complete}
            onBack={handleStep3Back}
            initialScenes={scenes}
          />
        )}
        
        {currentStep === 4 && (
          <Step4VideoProgress
            scenes={scenes}
            onComplete={handleStep4Complete}
            onCancel={handleStep4Cancel}
          />
        )}
        
        {currentStep === 5 && (
          <Step5ResultPreview
            videoUrl={videoUrl}
            videoMetadata={videoMetadata}
            onRegenerate={handleRegenerate}
          />
        )}
      </StepContainer>
    </main>
  );
}

