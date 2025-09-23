import React, { useState } from 'react';
import Header from '@/components/Header';
import TurnConfigForm from '@/components/TurnConfigForm';
import OptimizationForm from '@/components/OptimizationForm';
import OptimizationResults from '@/components/OptimizationResults';
import { Toaster } from '@/components/ui/toaster';
import { Card, CardContent } from '@/components/ui/card';

const Index: React.FC = () => {
  const [currentStep, setCurrentStep] = useState<'config' | 'optimize' | 'results'>('config');
  const [generatedConfig, setGeneratedConfig] = useState<any>(null);
  const [optimizationResult, setOptimizationResult] = useState<any>(null);
  const [processingStats, setProcessingStats] = useState({
    successful: 0,
    failed: 0,
    total: 0,
  });

  const handleConfigGenerated = (configData: any) => {
    setGeneratedConfig(configData);
    setCurrentStep('optimize');
    setProcessingStats(prev => ({
      ...prev,
      successful: prev.successful + 1,
      total: prev.total + 1
    }));
  };

  const handleOptimizationComplete = (result: any) => {
    setOptimizationResult(result);
    setCurrentStep('results');
    setProcessingStats(prev => ({
      ...prev,
      successful: prev.successful + 1,
      total: prev.total + 1
    }));
  };

  const handleNewOptimization = () => {
    setCurrentStep('config');
    setGeneratedConfig(null);
    setOptimizationResult(null);
  };

  const successRate = processingStats.total > 0 
    ? Math.round((processingStats.successful / processingStats.total) * 100)
    : 0;

  return (
    <div className="min-h-screen bg-background">
      <Header />
      
      {/* Main Content */}
      <main className="min-h-[calc(100vh-80px)] bg-gradient-to-br from-background via-background to-accent/10">
        <div className="container mx-auto px-4 py-8">
          <div className="max-w-6xl mx-auto">
            {/* Hero Section */}
            <div className="text-center mb-12">
              <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
                Sistema inteligente de optimización de turnos para maximizar eficiencia y minimizar costos
              </p>
            </div>

            {/* Progress Steps */}
            <div className="flex justify-center mb-8">
              <div className="flex items-center space-x-4">
                <div className={`flex items-center gap-2 px-4 py-2 rounded-full ${
                  currentStep === 'config' ? 'bg-primary text-primary-foreground' : 
                  generatedConfig ? 'bg-success/20 text-success' : 'bg-muted text-muted-foreground'
                }`}>
                  <span className="w-6 h-6 rounded-full bg-current opacity-20 flex items-center justify-center text-xs">1</span>
                  Configuración
                </div>
                <div className="w-8 h-px bg-border"></div>
                <div className={`flex items-center gap-2 px-4 py-2 rounded-full ${
                  currentStep === 'optimize' ? 'bg-primary text-primary-foreground' : 
                  optimizationResult ? 'bg-success/20 text-success' : 'bg-muted text-muted-foreground'
                }`}>
                  <span className="w-6 h-6 rounded-full bg-current opacity-20 flex items-center justify-center text-xs">2</span>
                  Optimización
                </div>
                <div className="w-8 h-px bg-border"></div>
                <div className={`flex items-center gap-2 px-4 py-2 rounded-full ${
                  currentStep === 'results' ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'
                }`}>
                  <span className="w-6 h-6 rounded-full bg-current opacity-20 flex items-center justify-center text-xs">3</span>
                  Resultados
                </div>
              </div>
            </div>

            {/* Content */}
            {currentStep === 'config' && (
              <TurnConfigForm onConfigGenerated={handleConfigGenerated} />
            )}
            
            {currentStep === 'optimize' && generatedConfig && (
              <OptimizationForm 
                config={generatedConfig.config}
                optimizationStrategy={generatedConfig.optimizationStrategy}
                sundayStrategy={generatedConfig.sundayStrategy}
                onOptimizationComplete={handleOptimizationComplete} 
              />
            )}
            
            {currentStep === 'results' && optimizationResult && (
              <OptimizationResults 
                result={optimizationResult} 
                onNewOptimization={handleNewOptimization} 
              />
            )}

            {/* Stats Section */}
            {processingStats.total > 0 && (
              <Card className="card-elegant mt-8">
                <CardContent className="p-6">
                  <div className="grid grid-cols-3 gap-6">
                    <div className="text-center p-4 gradient-success rounded-xl text-white">
                      <div className="text-2xl font-bold">{processingStats.successful}</div>
                      <div className="text-xs opacity-90">Configuraciones exitosas</div>
                    </div>
                    <div className="text-center p-4 gradient-secondary rounded-xl text-white">
                      <div className="text-2xl font-bold">{processingStats.failed}</div>
                      <div className="text-xs opacity-90">Fallidas</div>
                    </div>
                    <div className="text-center p-4 gradient-primary rounded-xl text-white">
                      <div className="text-2xl font-bold">{successRate}%</div>
                      <div className="text-xs opacity-90">Eficiencia</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mt-8">
        <a 
          href="https://youtube.com" 
          target="_blank" 
          rel="noopener noreferrer"
          className="text-black hover:text-gray-800 transition-colors underline-offset-4 hover:underline text-lg font-medium"
        >
          Ver video explicativo
        </a>
      </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="py-8 bg-muted/20">
        <div className="container mx-auto px-6 text-center">
          <p className="text-sm text-muted-foreground">
            SERVAGRO Shift Scheduler - Sistema profesional de optimización de turnos
          </p>
        </div>
      </footer>

      <Toaster />
    </div>
  );
};

export default Index;
