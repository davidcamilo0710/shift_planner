import React, { useState } from 'react';
import { useToast } from '@/hooks/use-toast';
import StepPostsCount from './StepPostsCount';
import StepEmployeesConfig from './StepEmployeesConfig';
import StepSalariesConfig from './StepSalariesConfig';
import { AdvancedConfig } from './AdvancedSettings';

interface PostConfig {
  employeesCount: number;
}

interface ConfigFormProps {
  onConfigGenerated: (config: any) => void;
}

type Step = 'posts' | 'employees' | 'salaries';

const TurnConfigForm: React.FC<ConfigFormProps> = ({ onConfigGenerated }) => {
  const [currentStep, setCurrentStep] = useState<Step>('posts');
  const [postsCount, setPostsCount] = useState(0);
  const [postsConfig, setPostsConfig] = useState<PostConfig[]>([]);
  const [comodinesCount, setComodinesCount] = useState(0);
  const [isGenerating, setIsGenerating] = useState(false);
  const { toast } = useToast();

  const [storedYear, setStoredYear] = useState(2025);
  const [storedMonth, setStoredMonth] = useState(8);
  const [storedAdvancedConfig, setStoredAdvancedConfig] = useState<AdvancedConfig | null>(null);
  const [selectedOptimizationStrategy, setSelectedOptimizationStrategy] = useState('lexicographic');
  const [selectedSundayStrategy, setSelectedSundayStrategy] = useState('smart');

  const handlePostsCountNext = (count: number, year: number, month: number, advancedConfig: AdvancedConfig, optimizationStrategy: string, sundayStrategy: string) => {
    setPostsCount(count);
    setStoredYear(year);
    setStoredMonth(month);
    setStoredAdvancedConfig(advancedConfig);
    setSelectedOptimizationStrategy(optimizationStrategy);
    setSelectedSundayStrategy(sundayStrategy);
    setCurrentStep('employees');
  };

  const handleEmployeesConfigNext = (config: PostConfig[], comodines: number) => {
    setPostsConfig(config);
    setComodinesCount(comodines);
    setCurrentStep('salaries');
  };

  const handleSalariesConfigNext = async (salariesData: any) => {
    setIsGenerating(true);
    
    try {
      // Usar la configuración avanzada si está disponible, sino usar valores por defecto
      const advancedConfig = storedAdvancedConfig || {
        dayStart: '06:00',
        nightStart: '21:00',
        rn_pct: 0.35,
        rf_pct: 0.75,
        he_pct: 0.25,
        hoursBaseMonth: 192,
        hoursPerWeek: 48,
        minFixedPerPost: 3,
        shiftLengthHours: 12,
        firstShiftStart: '06:00',
        sundayThreshold: 2,
        maxPostsPerComodin: 5,
        minRestHours: 0,
        useLexicographic: true,
        w_HE: 1000,
        w_RF: 800,
        w_RN: 600,
        w_BASE: 1
      };

      // Obtener festivos del año correspondiente
      let yearHolidays = [];
      try {
        const holidaysResponse = await fetch(`https://coral-app-fvng6.ondigitalocean.app/holidays/${storedYear}`);
        if (holidaysResponse.ok) {
          const holidaysData = await holidaysResponse.json();
          yearHolidays = holidaysData.holidays || [];
        }
      } catch (error) {
        console.warn('No se pudieron cargar los festivos:', error);
      }

      // Crear la configuración completa para la API
      const fullConfig = {
        global_config: {
          year: storedYear,
          month: storedMonth,
          hours_per_week: advancedConfig.hoursPerWeek,
          hours_base_month: advancedConfig.hoursBaseMonth,
          shift_length_hours: advancedConfig.shiftLengthHours,
          shift_start_time: advancedConfig.firstShiftStart,
          day_start: advancedConfig.dayStart,
          night_start: advancedConfig.nightStart,
          sunday_threshold: advancedConfig.sundayThreshold,
          min_fixed_per_post: advancedConfig.minFixedPerPost,
          max_posts_per_comodin: advancedConfig.maxPostsPerComodin,
          he_pct: advancedConfig.he_pct,
          rf_pct: advancedConfig.rf_pct,
          rn_pct: advancedConfig.rn_pct,
          w_he: advancedConfig.w_HE,
          w_rf: advancedConfig.w_RF,
          w_rn: advancedConfig.w_RN,
          w_base: advancedConfig.w_BASE,
          use_lexicographic: advancedConfig.useLexicographic
        },
        holidays: yearHolidays,
        posts_count: postsCount,
        posts_config: salariesData.postsConfig,
        comodines_count: salariesData.comodines_count,
        comodines_salaries: salariesData.comodines_salaries
      };

      console.log('Configuración completa generada:', fullConfig);

      // Validar la configuración
      const validateResponse = await fetch('https://coral-app-fvng6.ondigitalocean.app/config/validate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(fullConfig),
      });

      if (!validateResponse.ok) {
        const errorData = await validateResponse.json().catch(() => null);
        throw new Error(errorData?.detail || `Error de validación ${validateResponse.status}`);
      }

      const validationResult = await validateResponse.json();
      console.log('Resultado de validación:', validationResult);

      if (!validationResult.valid) {
        throw new Error(`Configuración inválida: ${validationResult.errors.join(', ')}`);
      }

      toast({
        title: "¡Configuración generada exitosamente!",
        description: `${validationResult.total_fijos} empleados fijos + ${validationResult.total_comodines} comodines en ${validationResult.total_posts} puestos`,
      });

      onConfigGenerated({
        config: fullConfig,
        summary: `Configuración generada: ${validationResult.total_posts} puestos, ${validationResult.total_fijos} empleados fijos, ${validationResult.total_comodines || 0} comodines`,
        employee_count: validationResult.total_fijos + (validationResult.total_comodines || 0),
        post_count: validationResult.total_posts,
        validation: validationResult,
        optimizationStrategy: selectedOptimizationStrategy,
        sundayStrategy: selectedSundayStrategy
      });

    } catch (error) {
      console.error('Error generando configuración:', error);
      
      let errorMessage = "Error generando la configuración";
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      
      toast({
        title: "Error en la configuración",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleBack = () => {
    if (currentStep === 'employees') {
      setCurrentStep('posts');
    } else if (currentStep === 'salaries') {
      setCurrentStep('employees');
    }
  };

  if (isGenerating) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="text-center p-8">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent mx-auto mb-4" />
          <h3 className="text-xl font-semibold mb-2">Generando configuración...</h3>
          <p className="text-muted-foreground">Procesando los datos de empleados y salarios</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {currentStep === 'posts' && (
        <StepPostsCount onNext={handlePostsCountNext} />
      )}
      
      {currentStep === 'employees' && (
        <StepEmployeesConfig 
          postsCount={postsCount}
          onNext={handleEmployeesConfigNext}
          onBack={handleBack}
        />
      )}
      
      {currentStep === 'salaries' && (
        <StepSalariesConfig 
          postsCount={postsCount}
          postsConfig={postsConfig}
          comodinesCount={comodinesCount}
          onNext={handleSalariesConfigNext}
          onBack={handleBack}
        />
      )}
    </div>
  );
};

export default TurnConfigForm;