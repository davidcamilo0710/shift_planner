import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { ArrowRight, ArrowLeft, Users, Star } from 'lucide-react';

interface PostConfig {
  employeesCount: number;
}

interface StepEmployeesConfigProps {
  postsCount: number;
  onNext: (postsConfig: PostConfig[], comodinesCount: number) => void;
  onBack: () => void;
}

const StepEmployeesConfig: React.FC<StepEmployeesConfigProps> = ({ 
  postsCount, 
  onNext, 
  onBack 
}) => {
  const [postsConfig, setPostsConfig] = useState<PostConfig[]>(
    Array.from({ length: postsCount }, () => ({ employeesCount: 3 }))
  );
  const [hasComodines, setHasComodines] = useState(true);
  const [comodinesCount, setComodinesCount] = useState(2);
  const updatePostEmployees = (postIndex: number, count: number) => {
    const newConfig = [...postsConfig];
    newConfig[postIndex] = { employeesCount: count };
    setPostsConfig(newConfig);
  };

  const totalEmployees = postsConfig.reduce((sum, post) => sum + post.employeesCount, 0);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onNext(postsConfig, hasComodines ? comodinesCount : 0);
  };

  return (
    <Card className="card-professional max-w-4xl mx-auto">
      <div className="p-8">
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
            <Users className="w-8 h-8 text-primary" />
          </div>
          <h2 className="text-3xl font-bold mb-2">Configurar empleados por puesto</h2>
          <p className="text-muted-foreground text-lg">
            Define cuántos empleados necesitas para cada puesto de trabajo
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Configuración por puesto */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-semibold">Empleados por puesto</h3>
              <AdvancedSettings 
                config={advancedConfig} 
                onConfigChange={setAdvancedConfig} 
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {postsConfig.map((post, index) => (
                <div key={index} className="bg-accent/20 rounded-xl p-4">
                  <Label htmlFor={`post-${index}`} className="font-medium">
                    Puesto {index + 1}
                  </Label>
                  <Input
                    id={`post-${index}`}
                    type="number"
                    min="1"
                    max="10"
                    value={post.employeesCount}
                    onChange={(e) => updatePostEmployees(index, parseInt(e.target.value) || 1)}
                    className="mt-2 text-center"
                  />
                  <p className="text-xs text-muted-foreground mt-1 text-center">
                    {post.employeesCount} empleado{post.employeesCount !== 1 ? 's' : ''}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Empleados COMODINES */}
          <div className="bg-warning/10 rounded-xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Star className="w-6 h-6 text-warning" />
                <div>
                  <h3 className="text-xl font-semibold">Empleados COMODINES</h3>
                  <p className="text-sm text-muted-foreground">
                    Empleados flexibles que pueden cubrir cualquier puesto según necesidad
                  </p>
                </div>
              </div>
              <Switch
                checked={hasComodines}
                onCheckedChange={setHasComodines}
              />
            </div>

            {hasComodines && (
              <div className="max-w-xs">
                <Label htmlFor="comodines">Cantidad de COMODINES</Label>
                <Input
                  id="comodines"
                  type="number"
                  min="0"
                  max="10"
                  value={comodinesCount}
                  onChange={(e) => setComodinesCount(parseInt(e.target.value) || 0)}
                  className="mt-2 text-center"
                />
              </div>
            )}
          </div>

          {/* Resumen */}
          <div className="bg-accent/30 rounded-xl p-6">
            <h4 className="font-medium mb-3">Resumen de configuración:</h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div className="text-center p-3 bg-primary/10 rounded-lg">
                <div className="text-2xl font-bold text-primary">{postsCount}</div>
                <div className="text-muted-foreground">Puestos</div>
              </div>
              <div className="text-center p-3 bg-secondary/10 rounded-lg">
                <div className="text-2xl font-bold text-secondary">{totalEmployees}</div>
                <div className="text-muted-foreground">Empleados Fijos</div>
              </div>
              <div className="text-center p-3 bg-warning/10 rounded-lg">
                <div className="text-2xl font-bold text-warning">{hasComodines ? comodinesCount : 0}</div>
                <div className="text-muted-foreground">Comodines</div>
              </div>
            </div>
            <div className="mt-4 text-center">
              <span className="text-lg font-semibold">
                Total empleados: {totalEmployees + (hasComodines ? comodinesCount : 0)}
              </span>
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
              Continuar
              <ArrowRight className="w-5 h-5 ml-2" />
            </Button>
          </div>
        </form>
      </div>
    </Card>
  );
};

export default StepEmployeesConfig;