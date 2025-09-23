import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Settings } from 'lucide-react';
import { Switch } from '@/components/ui/switch';

export interface AdvancedConfig {
  dayStart: string;        // Hora inicio del día para recargos (ej: "06:00")
  nightStart: string;      // Hora inicio de la noche para recargos (ej: "21:00")
  rn_pct: number;
  rf_pct: number;
  he_pct: number;
  hoursBaseMonth: number;
  hoursPerWeek: number;
  minFixedPerPost: number;
  shiftLengthHours: number;
  firstShiftStart: string; // Hora inicio del primer turno para rotaciones (ej: "06:00")
  sundayThreshold: number;
  maxPostsPerComodin: number;
  minRestHours: number;
  useLexicographic: boolean;
  w_HE: number;
  w_RF: number;
  w_RN: number;
  w_BASE: number;
}

interface AdvancedSettingsProps {
  config: AdvancedConfig;
  onConfigChange: (config: AdvancedConfig) => void;
}

const defaultAdvancedConfig: AdvancedConfig = {
  dayStart: '06:00',       // Inicio del día para recargos
  nightStart: '21:00',     // Inicio de la noche para recargos
  rn_pct: 0.35,
  rf_pct: 0.75,
  he_pct: 0.25,
  hoursBaseMonth: 192,
  hoursPerWeek: 48,
  minFixedPerPost: 3,
  shiftLengthHours: 12,
  firstShiftStart: '06:00', // Inicio del primer turno para rotaciones
  sundayThreshold: 2,
  maxPostsPerComodin: 5,
  minRestHours: 0,
  useLexicographic: true,
  w_HE: 1000,
  w_RF: 800,
  w_RN: 600,
  w_BASE: 1
};

const AdvancedSettings: React.FC<AdvancedSettingsProps> = ({ config, onConfigChange }) => {
  const [localConfig, setLocalConfig] = useState<AdvancedConfig>(config);

  const handleInputChange = (field: keyof AdvancedConfig, value: string | number | boolean) => {
    const newConfig = { ...localConfig, [field]: value };
    setLocalConfig(newConfig);
    onConfigChange(newConfig);
  };

  const resetToDefaults = () => {
    setLocalConfig(defaultAdvancedConfig);
    onConfigChange(defaultAdvancedConfig);
  };

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <Settings className="w-4 h-4" />
          Configuración Avanzada
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Configuración Avanzada del Sistema</DialogTitle>
        </DialogHeader>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Horarios */}
          <Card className="p-4">
            <h3 className="text-lg font-semibold mb-4">Configuración de Horarios</h3>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="dayStart">Inicio del Día (Recargos)</Label>
                  <Input
                    id="dayStart"
                    type="time"
                    value={localConfig.dayStart}
                    onChange={(e) => handleInputChange('dayStart', e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Para cálculo de recargos nocturnos
                  </p>
                </div>
                <div>
                  <Label htmlFor="nightStart">Inicio de la Noche (Recargos)</Label>
                  <Input
                    id="nightStart"
                    type="time"
                    value={localConfig.nightStart}
                    onChange={(e) => handleInputChange('nightStart', e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Para cálculo de recargos nocturnos
                  </p>
                </div>
              </div>
              
              <div className="border-t pt-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="firstShiftStart">Hora Inicio Primer Turno</Label>
                    <Input
                      id="firstShiftStart"
                      type="time"
                      value={localConfig.firstShiftStart}
                      onChange={(e) => handleInputChange('firstShiftStart', e.target.value)}
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Para calcular rotación de turnos
                    </p>
                  </div>
                  <div>
                    <Label htmlFor="shiftLengthHours">Duración del Turno</Label>
                    <select 
                      id="shiftLengthHours"
                      value={localConfig.shiftLengthHours}
                      onChange={(e) => handleInputChange('shiftLengthHours', parseInt(e.target.value))}
                      className="w-full p-2 border border-input rounded-md"
                    >
                      <option value={8}>8 horas (3 turnos)</option>
                      <option value={12}>12 horas (2 turnos)</option>
                    </select>
                    <p className="text-xs text-muted-foreground mt-1">
                      {localConfig.shiftLengthHours === 8 
                        ? `${localConfig.firstShiftStart}, +8h, +16h` 
                        : `${localConfig.firstShiftStart}, +12h`
                      }
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </Card>

          {/* Porcentajes */}
          <Card className="p-4">
            <h3 className="text-lg font-semibold mb-4">Porcentajes de Recargo</h3>
            <div className="space-y-4">
              <div>
                <Label htmlFor="rn_pct">Recargo Nocturno (%)</Label>
                <Input
                  id="rn_pct"
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  value={localConfig.rn_pct}
                  onChange={(e) => handleInputChange('rn_pct', parseFloat(e.target.value) || 0)}
                />
              </div>
              <div>
                <Label htmlFor="rf_pct">Recargo Festivo (%)</Label>
                <Input
                  id="rf_pct"
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  value={localConfig.rf_pct}
                  onChange={(e) => handleInputChange('rf_pct', parseFloat(e.target.value) || 0)}
                />
              </div>
              <div>
                <Label htmlFor="he_pct">Horas Extra (%)</Label>
                <Input
                  id="he_pct"
                  type="number"
                  step="0.01"
                  min="0"
                  max="2"
                  value={localConfig.he_pct}
                  onChange={(e) => handleInputChange('he_pct', parseFloat(e.target.value) || 0)}
                />
              </div>
            </div>
          </Card>

          {/* Límites de Trabajo */}
          <Card className="p-4">
            <h3 className="text-lg font-semibold mb-4">Límites de Trabajo</h3>
            <div className="space-y-4">
              <div>
                <Label htmlFor="hoursBaseMonth">Horas Base Mes</Label>
                <Input
                  id="hoursBaseMonth"
                  type="number"
                  min="100"
                  max="300"
                  value={localConfig.hoursBaseMonth}
                  onChange={(e) => handleInputChange('hoursBaseMonth', parseInt(e.target.value) || 220)}
                />
              </div>
              <div>
                <Label htmlFor="hoursPerWeek">Horas por Semana</Label>
                <Input
                  id="hoursPerWeek"
                  type="number"
                  min="30"
                  max="60"
                  value={localConfig.hoursPerWeek}
                  onChange={(e) => handleInputChange('hoursPerWeek', parseInt(e.target.value) || 44)}
                />
              </div>
              <div>
                <Label htmlFor="minRestHours">Mínimo Horas Descanso</Label>
                <Input
                  id="minRestHours"
                  type="number"
                  min="8"
                  max="24"
                  value={localConfig.minRestHours}
                  onChange={(e) => handleInputChange('minRestHours', parseInt(e.target.value) || 10)}
                />
              </div>
            </div>
          </Card>

          {/* Configuración de Empleados */}
          <Card className="p-4">
            <h3 className="text-lg font-semibold mb-4">Configuración de Empleados</h3>
            <div className="space-y-4">
              <div>
                <Label htmlFor="minFixedPerPost">Mínimo Fijos por Puesto</Label>
                <Input
                  id="minFixedPerPost"
                  type="number"
                  min="1"
                  max="10"
                  value={localConfig.minFixedPerPost}
                  onChange={(e) => handleInputChange('minFixedPerPost', parseInt(e.target.value) || 3)}
                />
              </div>
              <div>
                <Label htmlFor="sundayThreshold">Límite Domingos</Label>
                <Input
                  id="sundayThreshold"
                  type="number"
                  min="1"
                  max="5"
                  value={localConfig.sundayThreshold}
                  onChange={(e) => handleInputChange('sundayThreshold', parseInt(e.target.value) || 2)}
                />
              </div>
              <div>
                <Label htmlFor="maxPostsPerComodin">Máx. Puestos por Comodín</Label>
                <Input
                  id="maxPostsPerComodin"
                  type="number"
                  min="1"
                  max="10"
                  value={localConfig.maxPostsPerComodin}
                  onChange={(e) => handleInputChange('maxPostsPerComodin', parseInt(e.target.value) || 4)}
                />
              </div>
            </div>
          </Card>

          {/* Algoritmo de Optimización */}
          <Card className="p-4 md:col-span-2">
            <h3 className="text-lg font-semibold mb-4">Algoritmo de Optimización</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-center space-x-2">
                <Switch
                  checked={localConfig.useLexicographic}
                  onCheckedChange={(checked) => handleInputChange('useLexicographic', checked)}
                />
                <Label>Usar Algoritmo Lexicográfico</Label>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="w_HE">Peso HE</Label>
                  <Input
                    id="w_HE"
                    type="number"
                    min="1"
                    max="1000"
                    value={localConfig.w_HE}
                    onChange={(e) => handleInputChange('w_HE', parseInt(e.target.value) || 100)}
                  />
                </div>
                <div>
                  <Label htmlFor="w_RF">Peso RF</Label>
                  <Input
                    id="w_RF"
                    type="number"
                    min="1"
                    max="100"
                    value={localConfig.w_RF}
                    onChange={(e) => handleInputChange('w_RF', parseInt(e.target.value) || 10)}
                  />
                </div>
                <div>
                  <Label htmlFor="w_RN">Peso RN</Label>
                  <Input
                    id="w_RN"
                    type="number"
                    min="1"
                    max="100"
                    value={localConfig.w_RN}
                    onChange={(e) => handleInputChange('w_RN', parseInt(e.target.value) || 1)}
                  />
                </div>
                <div>
                  <Label htmlFor="w_BASE">Peso BASE</Label>
                  <Input
                    id="w_BASE"
                    type="number"
                    min="1"
                    max="100"
                    value={localConfig.w_BASE}
                    onChange={(e) => handleInputChange('w_BASE', parseInt(e.target.value) || 1)}
                  />
                </div>
              </div>
            </div>
          </Card>
        </div>

        <div className="flex justify-between mt-6">
          <Button variant="outline" onClick={resetToDefaults}>
            Restablecer por Defecto
          </Button>
          <p className="text-sm text-muted-foreground">
            Los cambios se guardan automáticamente
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default AdvancedSettings;
export { defaultAdvancedConfig };