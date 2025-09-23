import React, { useState, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { useToast } from '@/hooks/use-toast';
import { Upload, FileSpreadsheet, CheckCircle2, Download } from 'lucide-react';

interface FileUploadProps {
  onFileProcessed?: (success: boolean) => void;
}

const FileUpload: React.FC<FileUploadProps> = ({ onFileProcessed }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [lastResultUrl, setLastResultUrl] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  const validateFile = (file: File): boolean => {
    // Check file type
    if (!file.name.endsWith('.xlsx')) {
      toast({
        title: "Archivo inválido",
        description: "Por favor selecciona un archivo .xlsx",
        variant: "destructive",
      });
      return false;
    }

    // Check file name
    if (file.name !== 'optimizer_config.xlsx') {
      toast({
        title: "Nombre de archivo incorrecto",
        description: "El archivo debe llamarse exactamente 'optimizer_config.xlsx'",
        variant: "destructive",
      });
      return false;
    }

    return true;
  };

  const handleFileSelect = (file: File) => {
    if (file && validateFile(file)) {
      setSelectedFile(file);
    } else {
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleFileInput = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) handleFileSelect(file);
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    
    const files = event.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
  };

  const downloadExampleFile = () => {
    const link = document.createElement('a');
    link.href = '/optimizer_config_example.xlsx';
    link.download = 'optimizer_config.xlsx';
    link.click();
    
    toast({
      title: "Descarga iniciada",
      description: "El archivo de ejemplo se está descargando",
    });
  };

  const downloadResult = () => {
    if (lastResultUrl) {
      const link = document.createElement('a');
      link.href = lastResultUrl;
      link.download = 'results.xlsx';
      link.click();
      
      toast({
        title: "Descarga iniciada",
        description: "El archivo de resultados se está descargando",
      });
    }
  };

  const processFile = async () => {
    if (!selectedFile) return;

    setIsProcessing(true);
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
      }, 200);

      const formData = new FormData();
      formData.append('config_file', selectedFile);
      formData.append('strategy', 'lexicographic');
      formData.append('log_level', 'INFO');
      formData.append('generate_validation', 'false');

      console.log('Iniciando petición a la API...');
      console.log('Archivo:', selectedFile.name, selectedFile.size, 'bytes');

      const response = await fetch('https://coral-app-fvng6.ondigitalocean.app/process', {
        method: 'POST',
        headers: {
          'accept': 'application/json',
        },
        body: formData,
        mode: 'cors',
      });

      clearInterval(progressInterval);
      setProgress(100);

      console.log('Respuesta recibida:', response.status, response.statusText);

      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Sin detalles del error');
        console.log('Error del servidor:', errorText);
        throw new Error(`Error del servidor (${response.status}): ${errorText}`);
      }

      // Handle binary response (Excel file)
      console.log('Procesando respuesta binaria...');
      const blob = await response.blob();
      console.log('Blob recibido:', blob.size, 'bytes, tipo:', blob.type);
      
      const url = window.URL.createObjectURL(blob);
      setLastResultUrl(url);

      // Auto-download the result
      const link = document.createElement('a');
      link.href = url;
      link.download = 'results.xlsx';
      link.click();

      console.log('Descarga iniciada automáticamente');

      toast({
        title: "¡Procesamiento exitoso!",
        description: "El archivo ha sido procesado y descargado automáticamente",
      });

      onFileProcessed?.(true);
    } catch (error) {
      console.error('Error completo del procesamiento:', error);
      
      let errorMessage = "Error de conexión con el servidor";
      
      if (error instanceof Error) {
        if (error.message.includes('Failed to fetch')) {
          errorMessage = "No se puede conectar con la API. Verifica tu conexión a internet.";
        } else if (error.message.includes('CORS')) {
          errorMessage = "Error CORS. El servidor debe permitir peticiones desde este dominio.";
        } else {
          errorMessage = error.message;
        }
      }
      
      toast({
        title: "Error en el procesamiento",
        description: errorMessage,
        variant: "destructive",
      });
      onFileProcessed?.(false);
    } finally {
      setIsProcessing(false);
      setProgress(0);
    }
  };

  return (
    <div className="space-y-6">
      {/* File Upload Card */}
      <Card className="card-elegant">
        <div className="p-8">
          <div 
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            className={`text-center space-y-6 border-2 border-dashed rounded-2xl p-8 transition-all ${
              isDragging 
                ? 'border-primary bg-primary/5' 
                : 'border-border hover:border-primary/50'
            }`}
          >
            <div className={`mx-auto w-16 h-16 rounded-2xl flex items-center justify-center transition-colors ${
              isDragging ? 'bg-primary text-white' : 'bg-accent text-accent-foreground'
            }`}>
              <Upload className="w-8 h-8" />
            </div>
            
            <div>
              <h3 className="text-xl font-semibold mb-2">
                {isDragging ? 'Suelta el archivo aquí' : 'Subir Archivo de Configuración'}
              </h3>
              <p className="text-muted-foreground">
                Arrastra tu archivo optimizer_config.xlsx o haz clic para seleccionar
              </p>
            </div>

            <div className="space-y-4">
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx"
                onChange={handleFileInput}
                className="hidden"
                id="file-upload"
              />
              
              <label
                htmlFor="file-upload"
                className="inline-flex items-center justify-center gap-2 px-8 py-4 border border-border rounded-xl hover:border-primary transition-smooth cursor-pointer bg-background hover:bg-accent/50"
              >
                <FileSpreadsheet className="w-5 h-5 text-muted-foreground" />
                <span className="font-medium">
                  {selectedFile ? selectedFile.name : 'Seleccionar archivo optimizer_config.xlsx'}
                </span>
              </label>

              {selectedFile && (
                <div className="flex items-center justify-center gap-2 text-sm text-success">
                  <CheckCircle2 className="w-4 h-4" />
                  Archivo válido seleccionado
                </div>
              )}
            </div>

            <Button
              onClick={processFile}
              disabled={!selectedFile || isProcessing}
              variant="hero"
              size="xl"
              className="w-full max-w-sm"
            >
              {isProcessing ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                  Procesando...
                </>
              ) : (
                <>
                  <FileSpreadsheet className="w-5 h-5" />
                  Procesar Archivo
                </>
              )}
            </Button>

            {isProcessing && (
              <div className="space-y-2">
                <Progress value={progress} className="w-full max-w-sm mx-auto" />
                <p className="text-sm text-muted-foreground">
                  Optimizando configuración... {Math.round(progress)}%
                </p>
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* Action Buttons */}
      <div className="flex justify-center gap-4">
        <Button
          onClick={downloadExampleFile}
          variant="secondary"
          size="lg"
        >
          <Download className="w-4 h-4" />
          Descargar Ejemplo
        </Button>

        {lastResultUrl && (
          <Button
            onClick={downloadResult}
            variant="success"
            size="lg"
          >
            <Download className="w-4 h-4" />
            Último Resultado
          </Button>
        )}
      </div>
    </div>
  );
};

export default FileUpload;