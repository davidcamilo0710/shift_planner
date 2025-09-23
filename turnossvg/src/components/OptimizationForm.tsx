import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { useToast } from '@/hooks/use-toast';
import { Zap, Target, Calendar, Shuffle, AlertCircle, CheckCircle2 } from 'lucide-react';

interface OptimizationFormProps {
  config: any;
  optimizationStrategy?: string;
  sundayStrategy?: string;
  onOptimizationComplete: (result: any) => void;
}

interface Strategies {
  optimization_strategies: Record<string, string>;
  sunday_strategies: Record<string, string>;
  recommended: {
    strategy: string;
    sunday_strategy: string;
  };
}

const OptimizationForm: React.FC<OptimizationFormProps> = ({ 
  config, 
  optimizationStrategy = 'lexicographic', 
  sundayStrategy = 'smart', 
  onOptimizationComplete 
}) => {
  const [strategies, setStrategies] = useState<Strategies | null>(null);
  const [selectedStrategy, setSelectedStrategy] = useState(optimizationStrategy);
  const [selectedSundayStrategy, setSelectedSundayStrategy] = useState(sundayStrategy);
  const [seed, setSeed] = useState(42);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [validationResult, setValidationResult] = useState<any>(null);
  const { toast } = useToast();

  useEffect(() => {
    loadStrategies();
    validateConfig();
  }, [config]);

  const loadStrategies = async () => {
    try {
      const response = await fetch('https://coral-app-fvng6.ondigitalocean.app/strategies');
      if (response.ok) {
        const data = await response.json();
        setStrategies(data);
        setSelectedStrategy(data.recommended.strategy);
        setSelectedSundayStrategy(data.recommended.sunday_strategy);
      }
    } catch (error) {
      console.error('Error cargando estrategias:', error);
    }
  };

  const validateConfig = async () => {
    try {
      const response = await fetch('https://coral-app-fvng6.ondigitalocean.app/config/validate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
      });

      if (response.ok) {
        const result = await response.json();
        setValidationResult(result);
        
        if (result.errors.length > 0) {
          toast({
            title: "Errores en la configuración",
            description: result.errors.join(', '),
            variant: "destructive",
          });
        } else if (result.warnings.length > 0) {
          toast({
            title: "Advertencias",
            description: result.warnings.join(', '),
            variant: "default",
          });
        }
      }
    } catch (error) {
      console.error('Error validando configuración:', error);
    }
  };

  const runOptimization = async () => {
    if (!strategies) return;

    setIsOptimizing(true);
    setProgress(0);

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + Math.random() * 10;
        });
      }, 300);

      const optimizationRequest = {
        config: config,
        strategy: selectedStrategy,
        sunday_strategy: selectedSundayStrategy,
        seed: seed
      };

      console.log('Ejecutando optimización:', optimizationRequest);

      const response = await fetch('https://coral-app-fvng6.ondigitalocean.app/optimize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(optimizationRequest),
      });

      clearInterval(progressInterval);
      setProgress(100);

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || `Error ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      console.log('Optimización completada:', result);

      if (result.success) {
        toast({
          title: "¡Optimización exitosa!",
          description: `${result.message} - Tiempo: ${result.solve_time?.toFixed(2)}s`,
        });
        onOptimizationComplete(result);
      } else {
        throw new Error(result.message || 'Error en la optimización');
      }

    } catch (error) {
      console.error('Error en optimización:', error);
      
      let errorMessage = "Error ejecutando la optimización";
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      
      toast({
        title: "Error en la optimización",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsOptimizing(false);
      setProgress(0);
    }
  };

  if (!strategies) {
    return (
      <Card className="card-elegant">
        <div className="p-8 text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary border-t-transparent mx-auto mb-4" />
          <p className="text-muted-foreground">Cargando estrategias...</p>
        </div>
      </Card>
    );
  }

  return (
    <Card className="card-elegant">
      <div className="p-8">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
            <Target className="w-6 h-6 text-primary" />
          </div>
          <div>
            <h2 className="text-2xl font-bold">Estrategias de Optimización</h2>
            <p className="text-muted-foreground">Configure cómo se ejecutará la optimización de turnos</p>
          </div>
        </div>

        {/* Validación */}
        {validationResult && (
          <div className="mb-6">
            <div className={`p-4 rounded-xl border ${
              validationResult.valid 
                ? 'border-success/20 bg-success/5' 
                : 'border-destructive/20 bg-destructive/5'
            }`}>
              <div className="flex items-center gap-2 mb-2">
                {validationResult.valid ? (
                  <CheckCircle2 className="w-5 h-5 text-success" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-destructive" />
                )}
                <span className="font-medium">
                  {validationResult.valid ? 'Configuración válida' : 'Errores en configuración'}
                </span>
              </div>
              
              <div className="text-sm space-y-1">
                <p>• {validationResult.total_posts} puestos, {validationResult.total_fijos} empleados fijos, {validationResult.total_comodines} comodines</p>
                <p>• Estimación: {validationResult.estimated_shifts} turnos</p>
                {validationResult.warnings.length > 0 && (
                  <div className="mt-2">
                    <p className="font-medium text-warning">Advertencias:</p>
                    {validationResult.warnings.map((warning: string, i: number) => (
                      <p key={i} className="text-warning">• {warning}</p>
                    ))}
                  </div>
                )}
                {validationResult.errors.length > 0 && (
                  <div className="mt-2">
                    <p className="font-medium text-destructive">Errores:</p>
                    {validationResult.errors.map((error: string, i: number) => (
                      <p key={i} className="text-destructive">• {error}</p>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
          {/* Estrategia Principal */}
          <div>
            <Label className="text-base font-semibold mb-4 block">Estrategia Principal</Label>
            <RadioGroup value={selectedStrategy} onValueChange={setSelectedStrategy}>
              {Object.entries(strategies.optimization_strategies).map(([key, description]) => (
                <div key={key} className="flex items-start space-x-2">
                  <RadioGroupItem value={key} id={key} className="mt-1" />
                  <div className="grid gap-1.5 leading-none">
                    <Label
                      htmlFor={key}
                      className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                    >
                      {key === 'lexicographic' ? 'Lexicográfica' : 'Pesos Combinados'}
                      {key === strategies.recommended.strategy && (
                        <span className="ml-2 text-xs bg-primary/10 text-primary px-2 py-1 rounded">
                          Recomendada
                        </span>
                      )}
                    </Label>
                    <p className="text-xs text-muted-foreground">
                      {description}
                    </p>
                  </div>
                </div>
              ))}
            </RadioGroup>
          </div>

          {/* Estrategia de Domingos */}
          <div>
            <Label className="text-base font-semibold mb-4 block">Estrategia de Domingos</Label>
            <RadioGroup value={selectedSundayStrategy} onValueChange={setSelectedSundayStrategy}>
              {Object.entries(strategies.sunday_strategies).map(([key, description]) => (
                <div key={key} className="flex items-start space-x-2">
                  <RadioGroupItem value={key} id={`sunday-${key}`} className="mt-1" />
                  <div className="grid gap-1.5 leading-none">
                    <Label
                      htmlFor={`sunday-${key}`}
                      className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                    >
                      {key === 'smart' ? 'Inteligente' : key === 'balanced' ? 'Balanceada' : 'Costo Directo'}
                      {key === strategies.recommended.sunday_strategy && (
                        <span className="ml-2 text-xs bg-primary/10 text-primary px-2 py-1 rounded">
                          Recomendada
                        </span>
                      )}
                    </Label>
                    <p className="text-xs text-muted-foreground">
                      {description}
                    </p>
                  </div>
                </div>
              ))}
            </RadioGroup>
          </div>
        </div>

        {/* Semilla aleatoria */}
        <div className="mb-8">
          <Label htmlFor="seed" className="text-base font-semibold">
            Semilla aleatoria
          </Label>
          <div className="flex items-center gap-4 mt-2">
            <Input
              id="seed"
              type="number"
              value={seed}
              onChange={(e) => setSeed(parseInt(e.target.value) || 42)}
              className="w-32"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSeed(Math.floor(Math.random() * 10000))}
            >
              <Shuffle className="w-4 h-4 mr-2" />
              Aleatorio
            </Button>
            <p className="text-sm text-muted-foreground">
              Usar la misma semilla genera resultados reproducibles
            </p>
          </div>
        </div>

        {isOptimizing && (
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-2">
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-primary border-t-transparent" />
              <span className="font-medium">Optimizando turnos...</span>
            </div>
            <Progress value={progress} className="w-full" />
            <p className="text-sm text-muted-foreground mt-2">
              Esto puede tomar varios segundos dependiendo de la complejidad
            </p>
          </div>
        )}

        <Button
          onClick={runOptimization}
          disabled={isOptimizing || (validationResult && !validationResult.valid)}
          variant="hero"
          size="xl"
          className="w-full"
        >
          {isOptimizing ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
              Optimizando...
            </>
          ) : (
            <>
              <Zap className="w-5 h-5" />
              Optimizar Turnos
            </>
          )}
        </Button>
      </div>
    </Card>
  );
};

export default OptimizationForm;