import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { CheckCircle2, Clock, Users, DollarSign, Calendar, Download, RotateCcw, AlertTriangle } from 'lucide-react';

interface OptimizationResultsProps {
  result: any;
  onNewOptimization: () => void;
}

const OptimizationResults: React.FC<OptimizationResultsProps> = ({ result, onNewOptimization }) => {
  const [activeTab, setActiveTab] = useState('summary');

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
    }).format(value);
  };

  const formatHours = (hours: number) => {
    return `${hours.toFixed(1)}h`;
  };

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      'OPTIMAL': { variant: 'default' as const, color: 'text-success', label: 'ÓPTIMO' },
      'FEASIBLE': { variant: 'secondary' as const, color: 'text-warning', label: 'FACTIBLE' },
      'INFEASIBLE': { variant: 'destructive' as const, color: 'text-destructive', label: 'NO FACTIBLE' }
    };
    
    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.FEASIBLE;
    return (
      <Badge variant={config.variant} className={config.color}>
        {config.label}
      </Badge>
    );
  };

  const employeeMetrics = result.employee_metrics ? Object.values(result.employee_metrics) : [];
  const topEmployees = employeeMetrics
    .sort((a: any, b: any) => b.total_employee - a.total_employee)
    .slice(0, 10);

  const exportResults = () => {
    const dataStr = JSON.stringify(result, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `optimization-results-${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="card-elegant">
        <div className="p-8">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-success/10 flex items-center justify-center">
                <CheckCircle2 className="w-6 h-6 text-success" />
              </div>
              <div>
                <h2 className="text-2xl font-bold">Resultados de Optimización</h2>
                <p className="text-muted-foreground">{result.message}</p>
              </div>
            </div>
            <div className="flex gap-2">
              <Button onClick={exportResults} variant="outline">
                <Download className="w-4 h-4" />
                Exportar
              </Button>
              <Button onClick={onNewOptimization} variant="secondary">
                <RotateCcw className="w-4 h-4" />
                Nueva Optimización
              </Button>
            </div>
          </div>

          {/* Métricas principales */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-4 rounded-xl bg-accent/30">
              <div className="flex items-center justify-center gap-2 mb-2">
                {getStatusBadge(result.solver_status)}
              </div>
              <p className="text-sm text-muted-foreground">Estado</p>
            </div>
            
            <div className="text-center p-4 rounded-xl bg-accent/30">
              <div className="flex items-center justify-center gap-2 mb-2">
                <Clock className="w-4 h-4 text-primary" />
                <span className="font-bold">{result.solve_time?.toFixed(2)}s</span>
              </div>
              <p className="text-sm text-muted-foreground">Tiempo de cálculo</p>
            </div>
            
            <div className="text-center p-4 rounded-xl bg-accent/30">
              <div className="flex items-center justify-center gap-2 mb-2">
                <Users className="w-4 h-4 text-primary" />
                <span className="font-bold">{result.active_employees?.length || 0}</span>
              </div>
              <p className="text-sm text-muted-foreground">Empleados activos</p>
            </div>
            
            <div className="text-center p-4 rounded-xl bg-accent/30">
              <div className="flex items-center justify-center gap-2 mb-2">
                <DollarSign className="w-4 h-4 text-primary" />
                <span className="font-bold text-sm">{formatCurrency(result.total_metrics?.total_cost || 0)}</span>
              </div>
              <p className="text-sm text-muted-foreground">Costo total</p>
            </div>
          </div>
        </div>
      </Card>

      {/* Detalles */}
      <Card className="card-elegant">
        <div className="p-8">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="summary">Resumen</TabsTrigger>
              <TabsTrigger value="employees">Empleados</TabsTrigger>
              <TabsTrigger value="assignments">Asignaciones</TabsTrigger>
            </TabsList>
            
            <TabsContent value="summary" className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="p-4 rounded-xl border">
                  <h4 className="font-semibold mb-3">Costos</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span>Costo total:</span>
                      <span className="font-medium">{formatCurrency(result.total_metrics?.total_cost || 0)}</span>
                    </div>
                  </div>
                </div>
                
                <div className="p-4 rounded-xl border">
                  <h4 className="font-semibold mb-3">Horas Extra</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span>Total HE:</span>
                      <span className="font-medium">{formatHours(result.total_metrics?.total_he_hours || 0)}</span>
                    </div>
                  </div>
                </div>
                
                <div className="p-4 rounded-xl border">
                  <h4 className="font-semibold mb-3">Domingos</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span>Exceso domingos:</span>
                      <span className="font-medium">{result.total_metrics?.employees_with_excess_sundays || 0}</span>
                    </div>
                  </div>
                </div>
              </div>
            </TabsContent>
            
            <TabsContent value="employees" className="space-y-4">
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Empleado</TableHead>
                      <TableHead>Salario</TableHead>
                      <TableHead>Horas</TableHead>
                      <TableHead>Domingos</TableHead>
                      <TableHead>HE</TableHead>
                      <TableHead>Total</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {topEmployees.map((emp: any) => (
                      <TableRow key={emp.emp_id}>
                        <TableCell className="font-medium">{emp.emp_id}</TableCell>
                        <TableCell>{formatCurrency(emp.salario_contrato)}</TableCell>
                        <TableCell>{formatHours(emp.hours_assigned)}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            {emp.num_sundays}
                            {emp.num_sundays > 4 && (
                              <AlertTriangle className="w-3 h-3 text-warning" />
                            )}
                          </div>
                        </TableCell>
                        <TableCell>{formatHours(emp.he_hours)}</TableCell>
                        <TableCell className="font-medium">{formatCurrency(emp.total_employee)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              
              {employeeMetrics.length > 10 && (
                <p className="text-sm text-muted-foreground text-center">
                  Mostrando los 10 empleados con mayor costo total de {employeeMetrics.length}
                </p>
              )}
            </TabsContent>
            
            <TabsContent value="assignments" className="space-y-4">
              <div className="p-4 rounded-xl bg-accent/30">
                <h4 className="font-semibold mb-2">Asignaciones de turnos</h4>
                <p className="text-sm text-muted-foreground">
                  Se generaron {Object.keys(result.assignments || {}).length} asignaciones de turnos.
                </p>
                <p className="text-sm text-muted-foreground mt-2">
                  Use la función "Exportar" para obtener los detalles completos de todas las asignaciones.
                </p>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </Card>
    </div>
  );
};

export default OptimizationResults;