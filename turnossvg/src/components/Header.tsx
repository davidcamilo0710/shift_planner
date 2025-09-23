import React from 'react';
import { Badge } from '@/components/ui/badge';
import { FileSpreadsheet, Settings } from 'lucide-react';
import grupoSvgLogo from '@/assets/grupo-svg-logo.png';

const Header: React.FC = () => {
  return (
    <header className="gradient-hero text-primary-foreground">
      <div className="container mx-auto px-6 py-12">
        <div className="text-center space-y-8 max-w-4xl mx-auto">
          {/* Logo */}
          <div className="flex items-center justify-center mb-6">
            <img 
              src={grupoSvgLogo} 
              alt="Grupo SVG - Servicio, Vigilancia, Gestión" 
              className="h-16 w-auto filter drop-shadow-lg"
            />
          </div>

          {/* Main Title */}
          <div className="space-y-4">
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight">
              Planificador de Turnos 24/7
            </h1>
            <div className="flex items-center justify-center gap-3">
              <div className="w-12 h-1 gradient-secondary rounded-full"></div>
              <span className="text-white/60 font-medium">OPTIMIZA RECARGOS</span>
              <div className="w-12 h-1 gradient-secondary rounded-full"></div>
            </div>
            <div className="flex items-center justify-center gap-3 text-sm">
              <Badge className="bg-success/20 text-success-foreground border-success/30 px-3 py-1">HE</Badge>
              <Badge className="bg-warning/20 text-warning-foreground border-warning/30 px-3 py-1">RF</Badge>
              <Badge className="bg-primary/20 text-primary-foreground border-primary/30 px-3 py-1">RN</Badge>
            </div>
          </div>

          {/* Subtitle */}
          <p className="text-lg md:text-xl text-white/90 max-w-3xl mx-auto leading-relaxed">
            Sube tu archivo de configuración y descarga un plan mensual optimizado con costos y KPIs automatizados
          </p>

          {/* Features */}
          <div className="grid md:grid-cols-3 gap-6 mt-12 max-w-4xl mx-auto">
            <div className="text-center space-y-3 p-4 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10">
              <div className="w-12 h-12 gradient-secondary rounded-xl flex items-center justify-center mx-auto">
                <FileSpreadsheet className="w-6 h-6 text-white" />
              </div>
              <h3 className="font-semibold text-white">Configuración Inteligente</h3>
              <p className="text-sm text-white/70">Analiza empleados y horarios automáticamente</p>
            </div>
            
            <div className="text-center space-y-3 p-4 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10">
              <div className="w-12 h-12 gradient-primary rounded-xl flex items-center justify-center mx-auto">
                <Settings className="w-6 h-6 text-white" />
              </div>
              <h3 className="font-semibold text-white">Optimización 24/7</h3>
              <p className="text-sm text-white/70">Calcula la mejor distribución de turnos</p>
            </div>
            
            <div className="text-center space-y-3 p-4 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10">
              <div className="w-12 h-12 gradient-secondary rounded-xl flex items-center justify-center mx-auto">
                <FileSpreadsheet className="w-6 h-6 text-white" />
              </div>
              <h3 className="font-semibold text-white">Reportes & KPIs</h3>
              <p className="text-sm text-white/70">Genera planes detallados con costos</p>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;