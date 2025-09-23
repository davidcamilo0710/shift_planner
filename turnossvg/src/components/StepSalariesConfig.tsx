import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, DollarSign, Check } from 'lucide-react';
import AdvancedSettings, { defaultAdvancedConfig, AdvancedConfig } from './AdvancedSettings';

interface PostConfig {
  employeesCount: number;
}

interface StepSalariesConfigProps {
  postsCount: number;
  postsConfig: PostConfig[];
  comodinesCount: number;
  onNext: (salariesData: any) => void;
  onBack: () => void;
}

const StepSalariesConfig: React.FC<StepSalariesConfigProps> = ({ 
  postsCount,
  postsConfig, 
  comodinesCount,
  onNext, 
  onBack 
}) => {
  // Inicializar salarios por defecto
  const [postsSalaries, setPostsSalaries] = useState<number[][]>(() => 
    postsConfig.map(post => 
      Array.from({ length: post.employeesCount }, () => 1400000)
    )
  );
  
  const [comodinesSalaries, setComodinesSalaries] = useState<number[]>(() => 
    Array.from({ length: comodinesCount }, () => 1400000)
  );
  const [advancedConfig, setAdvancedConfig] = useState<AdvancedConfig>(defaultAdvancedConfig);

  const updatePostSalary = (postIndex: number, employeeIndex: number, salary: number) => {
    const newSalaries = [...postsSalaries];
    newSalaries[postIndex][employeeIndex] = salary;
    setPostsSalaries(newSalaries);
  };

  const updateComodinSalary = (comodinIndex: number, salary: number) => {
    const newSalaries = [...comodinesSalaries];
    newSalaries[comodinIndex] = salary;
    setComodinesSalaries(newSalaries);
  };

  const setAllSalaries = (baseSalary: number) => {
    setPostsSalaries(postsConfig.map(post => 
      Array.from({ length: post.employeesCount }, () => baseSalary)
    ));
    setComodinesSalaries(Array.from({ length: comodinesCount }, () => baseSalary));
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
    }).format(value);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Crear la estructura de datos que necesita la API
    const salariesData = {
      postsConfig: postsConfig.map((post, index) => ({
        post_id: `P${(index + 1).toString().padStart(3, '0')}`,
        fixed_employees_count: post.employeesCount,
        employee_salaries: postsSalaries[index]
      })),
      comodines_count: comodinesCount,
      comodines_salaries: comodinesSalaries
    };
    
    onNext(salariesData);
  };

  const totalEmployees = postsConfig.reduce((sum, post) => sum + post.employeesCount, 0) + comodinesCount;

  return (
    <Card className="card-professional max-w-4xl mx-auto">
      <div className="p-8">
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
            <DollarSign className="w-8 h-8 text-primary" />
          </div>
          <div className="flex items-center justify-center gap-4 mb-4">
            <h2 className="text-3xl font-bold">Configurar salarios</h2>
            <AdvancedSettings 
              config={advancedConfig} 
              onConfigChange={setAdvancedConfig} 
            />
          </div>
          <p className="text-muted-foreground text-lg">
            Define el salario individual para cada empleado
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Herramientas rápidas */}
          <div className="bg-accent/20 rounded-xl p-4">
            <h3 className="font-medium mb-4">Configuración rápida</h3>
            <div className="flex flex-wrap gap-2">
              {[1200000, 1400000, 1600000, 1800000, 2000000].map(salary => (
                <Button
                  key={salary}
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setAllSalaries(salary)}
                >
                  Todos a {formatCurrency(salary)}
                </Button>
              ))}
            </div>
          </div>

          {/* Salarios por puesto */}
          <div className="space-y-6">
            <h3 className="text-xl font-semibold">Salarios por puesto</h3>
            {postsConfig.map((post, postIndex) => (
              <div key={postIndex} className="bg-accent/10 rounded-xl p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Badge variant="secondary">Puesto {postIndex + 1}</Badge>
                  <span className="text-sm text-muted-foreground">
                    {post.employeesCount} empleado{post.employeesCount !== 1 ? 's' : ''}
                  </span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {Array.from({ length: post.employeesCount }, (_, employeeIndex) => (
                    <div key={employeeIndex} className="space-y-2">
                      <Label htmlFor={`post-${postIndex}-emp-${employeeIndex}`} className="text-sm">
                        Empleado {employeeIndex + 1}
                      </Label>
                      <Input
                        id={`post-${postIndex}-emp-${employeeIndex}`}
                        type="number"
                        min="500000"
                        max="10000000"
                        step="50000"
                        value={postsSalaries[postIndex][employeeIndex]}
                        onChange={(e) => updatePostSalary(postIndex, employeeIndex, parseInt(e.target.value) || 1400000)}
                      />
                      <p className="text-xs text-muted-foreground">
                        {formatCurrency(postsSalaries[postIndex][employeeIndex])}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Salarios COMODINES */}
          {comodinesCount > 0 && (
            <div className="space-y-4">
              <h3 className="text-xl font-semibold flex items-center gap-2">
                Salarios COMODINES
                <Badge variant="outline">{comodinesCount} empleado{comodinesCount !== 1 ? 's' : ''}</Badge>
              </h3>
              <div className="bg-warning/10 rounded-xl p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {Array.from({ length: comodinesCount }, (_, comodinIndex) => (
                    <div key={comodinIndex} className="space-y-2">
                      <Label htmlFor={`comodin-${comodinIndex}`} className="text-sm">
                        Comodín {comodinIndex + 1}
                      </Label>
                      <Input
                        id={`comodin-${comodinIndex}`}
                        type="number"
                        min="500000"
                        max="10000000"
                        step="50000"
                        value={comodinesSalaries[comodinIndex]}
                        onChange={(e) => updateComodinSalary(comodinIndex, parseInt(e.target.value) || 1400000)}
                      />
                      <p className="text-xs text-muted-foreground">
                        {formatCurrency(comodinesSalaries[comodinIndex])}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Resumen */}
          <div className="bg-accent/30 rounded-xl p-6">
            <h4 className="font-medium mb-3">Resumen final:</h4>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm text-center">
              <div className="p-3 bg-primary/10 rounded-lg">
                <div className="text-xl font-bold text-primary">{postsCount}</div>
                <div className="text-muted-foreground">Puestos</div>
              </div>
              <div className="p-3 bg-secondary/10 rounded-lg">
                <div className="text-xl font-bold text-secondary">
                  {postsConfig.reduce((sum, post) => sum + post.employeesCount, 0)}
                </div>
                <div className="text-muted-foreground">Empleados Fijos</div>
              </div>
              <div className="p-3 bg-warning/10 rounded-lg">
                <div className="text-xl font-bold text-warning">{comodinesCount}</div>
                <div className="text-muted-foreground">Comodines</div>
              </div>
              <div className="p-3 bg-success/10 rounded-lg">
                <div className="text-xl font-bold text-success">{totalEmployees}</div>
                <div className="text-muted-foreground">Total</div>
              </div>
            </div>
          </div>

          <div className="flex gap-4">
            <Button
              type="button"
              variant="outline"
              size="lg"
              onClick={onBack}
              className="flex-1"
            >
              <ArrowLeft className="w-5 h-5 mr-2" />
              Volver
            </Button>
            <Button
              type="submit"
              variant="hero"
              size="lg"
              className="flex-1"
            >
              <Check className="w-5 h-5 mr-2" />
              Generar Configuración
            </Button>
          </div>
        </form>
      </div>
    </Card>
  );
};

export default StepSalariesConfig;