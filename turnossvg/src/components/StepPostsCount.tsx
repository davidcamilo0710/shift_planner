import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { ArrowRight, Building, Calendar, Target } from 'lucide-react';
import AdvancedSettings, { defaultAdvancedConfig, AdvancedConfig } from './AdvancedSettings';

interface StepPostsCountProps {
  onNext: (postsCount: number, year: number, month: number, advancedConfig: AdvancedConfig, optimizationStrategy: string, sundayStrategy: string) => void;
}

interface Strategies {
  optimization_strategies: Record<string, string>;
  sunday_strategies: Record<string, string>;
  recommended: {
    strategy: string;
    sunday_strategy: string;
  };
}

const StepPostsCount: React.FC<StepPostsCountProps> = ({ onNext }) => {
  const [postsCount, setPostsCount] = useState(5);
  const [year, setYear] = useState(2025);
  const [month, setMonth] = useState(8);
  const [advancedConfig, setAdvancedConfig] = useState<AdvancedConfig>(defaultAdvancedConfig);
  const [strategies, setStrategies] = useState<Strategies | null>(null);
  const [optimizationStrategy, setOptimizationStrategy] = useState('lexicographic');
  const [sundayStrategy, setSundayStrategy] = useState('smart');

  useEffect(() => {
    loadStrategies();
  }, []);

  const loadStrategies = async () => {
    try {
      const response = await fetch('https://coral-app-fvng6.ondigitalocean.app/strategies');
      if (response.ok) {
        const data = await response.json();
        setStrategies(data);
        setOptimizationStrategy(data.recommended.strategy);
        setSundayStrategy(data.recommended.sunday_strategy);
      }
    } catch (error) {
      console.error('Error cargando estrategias:', error);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (postsCount >= 1 && postsCount <= 20) {
      onNext(postsCount, year, month, advancedConfig, optimizationStrategy, sundayStrategy);
    }
  };

  return (
    <Card className="card-professional max-w-4xl mx-auto">
      <div className="p-8">
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
            <Building className="w-8 h-8 text-primary" />
          </div>
          <div className="flex items-center justify-center gap-4 mb-4">
            <h2 className="text-3xl font-bold">¿Cuántos puestos necesitas?</h2>
            <AdvancedSettings 
              config={advancedConfig} 
              onConfigChange={setAdvancedConfig} 
            />
          </div>
          <p className="text-muted-foreground text-lg">
            Cada puesto representa una posición de trabajo que necesita ser cubierta durante los turnos
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Configuración de Período */}
          <div className="bg-accent/20 rounded-xl p-6 space-y-4">
            <div className="flex items-center gap-3 mb-4">
              <Calendar className="w-6 h-6 text-primary" />
              <h3 className="text-xl font-semibold">Período de Optimización</h3>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="year">Año</Label>
                <Select value={year.toString()} onValueChange={(value) => setYear(parseInt(value))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="2024">2024</SelectItem>
                    <SelectItem value="2025">2025</SelectItem>
                    <SelectItem value="2026">2026</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="month">Mes</Label>
                <Select value={month.toString()} onValueChange={(value) => setMonth(parseInt(value))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">Enero</SelectItem>
                    <SelectItem value="2">Febrero</SelectItem>
                    <SelectItem value="3">Marzo</SelectItem>
                    <SelectItem value="4">Abril</SelectItem>
                    <SelectItem value="5">Mayo</SelectItem>
                    <SelectItem value="6">Junio</SelectItem>
                    <SelectItem value="7">Julio</SelectItem>
                    <SelectItem value="8">Agosto</SelectItem>
                    <SelectItem value="9">Septiembre</SelectItem>
                    <SelectItem value="10">Octubre</SelectItem>
                    <SelectItem value="11">Noviembre</SelectItem>
                    <SelectItem value="12">Diciembre</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          <div className="text-center space-y-4">
            <Label htmlFor="posts" className="text-lg font-medium">
              Cantidad de puestos de trabajo
            </Label>
            <Input
              id="posts"
              type="number"
              min="1"
              max="20"
              value={postsCount}
              onChange={(e) => setPostsCount(parseInt(e.target.value) || 1)}
              className="text-center text-2xl h-16 max-w-32 mx-auto"
            />
            <p className="text-sm text-muted-foreground">
              Mínimo 1, máximo 20 puestos
            </p>
          </div>

          {/* Estrategias de Optimización */}
          {strategies && (
            <div className="bg-accent/20 rounded-xl p-6 space-y-6">
              <div className="flex items-center gap-3 mb-4">
                <Target className="w-6 h-6 text-primary" />
                <h3 className="text-xl font-semibold">Estrategias de Optimización</h3>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Estrategia Principal */}
                <div>
                  <Label className="text-base font-semibold mb-3 block">Estrategia Principal</Label>
                  <RadioGroup value={optimizationStrategy} onValueChange={setOptimizationStrategy}>
                    {Object.entries(strategies.optimization_strategies).map(([key, description]) => (
                      <div key={key} className="flex items-start space-x-2">
                        <RadioGroupItem value={key} id={key} className="mt-1" />
                        <div className="grid gap-1.5 leading-none">
                          <Label
                            htmlFor={key}
                            className="text-sm font-medium leading-none cursor-pointer"
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
                  <Label className="text-base font-semibold mb-3 block">Estrategia de Domingos</Label>
                  <RadioGroup value={sundayStrategy} onValueChange={setSundayStrategy}>
                    {Object.entries(strategies.sunday_strategies).map(([key, description]) => (
                      <div key={key} className="flex items-start space-x-2">
                        <RadioGroupItem value={key} id={`sunday-${key}`} className="mt-1" />
                        <div className="grid gap-1.5 leading-none">
                          <Label
                            htmlFor={`sunday-${key}`}
                            className="text-sm font-medium leading-none cursor-pointer"
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
            </div>
          )}

          <div className="bg-accent/30 rounded-xl p-4">
            <h4 className="font-medium mb-2">Información:</h4>
            <p className="text-sm text-muted-foreground">
              Un puesto es una posición específica que debe estar cubierta las 24 horas. 
              Por ejemplo: Portería, Vigilancia Perimetral, Control de Acceso, etc.
            </p>
          </div>

          <Button
            type="submit"
            variant="hero"
            size="xl"
            className="w-full"
            disabled={postsCount < 1 || postsCount > 20}
          >
            Continuar
            <ArrowRight className="w-5 h-5 ml-2" />
          </Button>
        </form>
      </div>
    </Card>
  );
};

export default StepPostsCount;