import React, { useState } from 'react';
import { Upload, FileText, BarChart3, Download, Loader2, CheckCircle, AlertCircle, X, Target } from 'lucide-react';

const API_BASE_URL = 'https://public-swot.onrender.com';

const App = () => {
  const [activeTab, setActiveTab] = useState('questions');
  const [questionsForm, setQuestionsForm] = useState({
    csvFile: null,
    businessName: '',
    apiKey: ''
  });
  const [swotForm, setSwotForm] = useState({
    csvFile: null,
    pdfFiles: [], // Changed to array for multiple files
    businessName: '',
    apiKey: ''
  });
  const [questionsLoading, setQuestionsLoading] = useState(false);
  const [swotLoading, setSwotLoading] = useState(false);
  const [actionPlanLoading, setActionPlanLoading] = useState(false);
  const [questionsResult, setQuestionsResult] = useState(null);
  const [swotResult, setSwotResult] = useState(null);
  const [actionPlanResult, setActionPlanResult] = useState(null);
  const [error, setError] = useState(null);

  const handleFileUpload = (file, form, field, setter) => {
    setter(prev => ({
      ...prev,
      [field]: file
    }));
  };

  const handleMultiplePdfUpload = (files) => {
    const fileArray = Array.from(files);
    setSwotForm(prev => ({
      ...prev,
      pdfFiles: [...prev.pdfFiles, ...fileArray]
    }));
  };

  const removePdfFile = (indexToRemove) => {
    setSwotForm(prev => ({
      ...prev,
      pdfFiles: prev.pdfFiles.filter((_, index) => index !== indexToRemove)
    }));
  };

  const generateQuestions = async (e) => {
    e.preventDefault();
    setQuestionsLoading(true);
    setError(null);
    setQuestionsResult(null);

    const formData = new FormData();
    formData.append('csv_file', questionsForm.csvFile);
    formData.append('business_name', questionsForm.businessName);
    formData.append('api_key', questionsForm.apiKey);

    try {
      const response = await fetch(`${API_BASE_URL}/api/generate-questions`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail?.message || data.detail || 'Error generating questions');
      }

      setQuestionsResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setQuestionsLoading(false);
    }
  };

  const generateSwot = async (e) => {
    e.preventDefault();
    setSwotLoading(true);
    setError(null);
    setSwotResult(null);
    setActionPlanResult(null); // Clear action plan when generating new SWOT

    const formData = new FormData();
    formData.append('csv_file', swotForm.csvFile);
    
    // Append multiple PDF files
    swotForm.pdfFiles.forEach((file, index) => {
      formData.append('pdf_files', file);
    });
    
    formData.append('business_name', swotForm.businessName);
    formData.append('api_key', swotForm.apiKey);

    try {
      const response = await fetch(`${API_BASE_URL}/api/generate-swot`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail?.message || data.detail || 'Error generating SWOT analysis');
      }

      setSwotResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setSwotLoading(false);
    }
  };

  const generateActionPlan = async () => {
    if (!swotResult) {
      setError("SWOT analysis must be generated first");
      return;
    }

    setActionPlanLoading(true);
    setError(null);
    setActionPlanResult(null);

    const formData = new FormData();
    formData.append('csv_file', swotForm.csvFile);
    
    // Append multiple PDF files
    swotForm.pdfFiles.forEach((file, index) => {
      formData.append('pdf_files', file);
    });
    
    formData.append('business_name', swotForm.businessName);
    formData.append('swot_analysis', swotResult.swot_analysis);
    formData.append('api_key', swotForm.apiKey);

    try {
      console.log('Calling action plan API...'); // Debug log
      const response = await fetch(`${API_BASE_URL}/api/generate-action-plan`, {
        method: 'POST',
        body: formData,
      });

      console.log('Response status:', response.status); // Debug log
      const data = await response.json();
      console.log('Response data:', data); // Debug log

      if (!response.ok) {
        throw new Error(data.detail?.message || data.detail || 'Error generating action plan');
      }

      setActionPlanResult(data);
    } catch (err) {
      console.error('Action plan error:', err); // Debug log
      setError(err.message);
    } finally {
      setActionPlanLoading(false);
    }
  };

  const downloadPdf = async (pdfId, filename) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/download-pdf/${pdfId}`);
      if (!response.ok) throw new Error('Download failed');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError('Failed to download PDF');
    }
  };

  const FileUploadBox = ({ file, onFileSelect, accept, label, icon: Icon }) => (
    <div className="relative">
      <input
        type="file"
        accept={accept}
        onChange={(e) => onFileSelect(e.target.files[0])}
        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        id={`file-${label}`}
      />
      <label
        htmlFor={`file-${label}`}
        className={`flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer transition-colors ${
          file
            ? 'border-green-400 bg-green-50'
            : 'border-gray-300 bg-gray-50 hover:bg-gray-100'
        }`}
      >
        <div className="flex flex-col items-center justify-center pt-5 pb-6">
          <Icon className={`w-8 h-8 mb-3 ${file ? 'text-green-500' : 'text-gray-400'}`} />
          <p className="mb-2 text-sm text-gray-500">
            {file ? (
              <span className="font-medium text-green-600">{file.name}</span>
            ) : (
              <>
                <span className="font-semibold">Click to upload</span> {label}
              </>
            )}
          </p>
          <p className="text-xs text-gray-500">{accept.toUpperCase()}</p>
        </div>
      </label>
    </div>
  );

  const MultipleFileUploadBox = ({ files, onFileSelect, accept, label, icon: Icon }) => (
    <div className="space-y-3">
      <div className="relative">
        <input
          type="file"
          accept={accept}
          multiple
          onChange={(e) => onFileSelect(e.target.files)}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          id={`multiple-file-${label}`}
        />
        <label
          htmlFor={`multiple-file-${label}`}
          className={`flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer transition-colors ${
            files.length > 0
              ? 'border-green-400 bg-green-50'
              : 'border-gray-300 bg-gray-50 hover:bg-gray-100'
          }`}
        >
          <div className="flex flex-col items-center justify-center pt-5 pb-6">
            <Icon className={`w-8 h-8 mb-3 ${files.length > 0 ? 'text-green-500' : 'text-gray-400'}`} />
            <p className="mb-2 text-sm text-gray-500">
              {files.length > 0 ? (
                <span className="font-medium text-green-600">
                  {files.length} file{files.length > 1 ? 's' : ''} selected
                </span>
              ) : (
                <>
                  <span className="font-semibold">Click to upload</span> {label}
                </>
              )}
            </p>
            <p className="text-xs text-gray-500">{accept.toUpperCase()} • Multiple files supported</p>
          </div>
        </label>
      </div>
      
      {/* Display selected files */}
      {files.length > 0 && (
        <div className="space-y-2 max-h-32 overflow-y-auto">
          {files.map((file, index) => (
            <div key={index} className="flex items-center justify-between bg-blue-50 p-2 rounded-lg">
              <div className="flex items-center space-x-2">
                <FileText className="w-4 h-4 text-blue-500" />
                <span className="text-sm text-blue-700 truncate">{file.name}</span>
                <span className="text-xs text-blue-500">
                  ({(file.size / 1024 / 1024).toFixed(1)} MB)
                </span>
              </div>
              <button
                type="button"
                onClick={() => removePdfFile(index)}
                className="text-red-500 hover:text-red-700 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white py-12">
        <div className="max-w-6xl mx-auto px-4 text-center">
          <h1 className="text-4xl font-bold mb-4"> AI SWOT Analysis Platform</h1>
          <p className="text-xl opacity-90">Génération de questionnaires personnalisés et analyses SWOT stratégiques</p>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Navigation Tabs */}
        <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg mb-8">
          <button
            onClick={() => setActiveTab('questions')}
            className={`flex-1 py-3 px-4 rounded-md font-medium transition-colors ${
              activeTab === 'questions'
                ? 'bg-white text-blue-600 shadow-sm'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            <FileText className="inline w-5 h-5 mr-2" />
            Générateur de Questions
          </button>
          <button
            onClick={() => setActiveTab('swot')}
            className={`flex-1 py-3 px-4 rounded-md font-medium transition-colors ${
              activeTab === 'swot'
                ? 'bg-white text-blue-600 shadow-sm'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            <BarChart3 className="inline w-5 h-5 mr-2" />
            Analyse SWOT
          </button>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-center">
              <AlertCircle className="w-5 h-5 text-red-500 mr-2" />
              <p className="text-red-700">{error}</p>
            </div>
          </div>
        )}

        {/* Questions Generator Tab */}
        {activeTab === 'questions' && (
          <div className="bg-white rounded-lg shadow-lg p-8">
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-gray-800 mb-2"> Générateur de Questions</h2>
              <p className="text-gray-600">Créez des questionnaires personnalisés de 50-100 questions diagnostiques basés sur le profil de votre entreprise.</p>
            </div>

            <form onSubmit={generateQuestions} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Fichier CSV des réponses de profilage
                  </label>
                  <FileUploadBox
                    file={questionsForm.csvFile}
                    onFileSelect={(file) => handleFileUpload(file, questionsForm, 'csvFile', setQuestionsForm)}
                    accept=".csv"
                    label="your CSV file"
                    icon={Upload}
                  />
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Nom de l'entreprise
                    </label>
                    <input
                      type="text"
                      value={questionsForm.businessName}
                      onChange={(e) => setQuestionsForm(prev => ({...prev, businessName: e.target.value}))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Entrez le nom exact de l'entreprise"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Clé API OpenAI
                    </label>
                    <input
                      type="password"
                      value={questionsForm.apiKey}
                      onChange={(e) => setQuestionsForm(prev => ({...prev, apiKey: e.target.value}))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="sk-..."
                      required
                    />
                  </div>
                </div>
              </div>

              <button
                type="submit"
                disabled={questionsLoading || !questionsForm.csvFile || !questionsForm.businessName || !questionsForm.apiKey}
                className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3 px-6 rounded-md font-medium hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                {questionsLoading ? (
                  <>
                    <Loader2 className="animate-spin inline w-5 h-5 mr-2" />
                    Génération en cours...
                  </>
                ) : (
                  'Générer les Questions'
                )}
              </button>
            </form>

            {/* Questions Result */}
            {questionsResult && (
              <div className="mt-8 p-6 bg-green-50 border border-green-200 rounded-lg">
                <div className="flex items-center mb-4">
                  <CheckCircle className="w-6 h-6 text-green-500 mr-2" />
                  <h3 className="text-lg font-semibold text-green-800">Questions générées avec succès!</h3>
                </div>
                <div className="space-y-2 mb-4">
                  <p><strong>Entreprise:</strong> {questionsResult.business_name}</p>
                  <p><strong>Nombre de questions:</strong> {questionsResult.questions_count}</p>
                </div>
                
                {questionsResult.questions_preview && (
                  <div className="mb-4">
                    <h4 className="font-medium mb-2">Aperçu des questions:</h4>
                    <ul className="space-y-1 text-sm">
                      {questionsResult.questions_preview.map((question, index) => (
                        <li key={index} className="flex items-start">
                          <span className="font-medium mr-2">{index + 1}.</span>
                          <span>{question}</span>
                        </li>
                      ))}
                    </ul>
                    <p className="text-sm text-gray-600 mt-2">... et {questionsResult.questions_count - 5} questions supplémentaires dans le PDF</p>
                  </div>
                )}

                <button
                  onClick={() => downloadPdf(questionsResult.pdf_id, `${questionsResult.business_name}_questionnaire.pdf`)}
                  className="bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 transition-colors"
                >
                  <Download className="inline w-4 h-4 mr-2" />
                  Télécharger le PDF
                </button>
              </div>
            )}
          </div>
        )}

        {/* SWOT Analysis Tab */}
        {activeTab === 'swot' && (
          <div className="bg-white rounded-lg shadow-lg p-8">
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-gray-800 mb-2">Analyse SWOT</h2>
              <p className="text-gray-600">Générez une analyse SWOT stratégique complète à partir des réponses détaillées de votre entreprise. Vous pouvez uploader plusieurs fichiers PDF.</p>
            </div>

            <form onSubmit={generateSwot} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Fichier CSV de profilage
                    </label>
                    <FileUploadBox
                      file={swotForm.csvFile}
                      onFileSelect={(file) => handleFileUpload(file, swotForm, 'csvFile', setSwotForm)}
                      accept=".csv"
                      label="your CSV file"
                      icon={Upload}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Fichiers PDF des Q&A détaillées (Multiples fichiers supportés)
                    </label>
                    <MultipleFileUploadBox
                      files={swotForm.pdfFiles}
                      onFileSelect={handleMultiplePdfUpload}
                      accept=".pdf"
                      label="your PDF files"
                      icon={FileText}
                    />
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Nom de l'entreprise
                    </label>
                    <input
                      type="text"
                      value={swotForm.businessName}
                      onChange={(e) => setSwotForm(prev => ({...prev, businessName: e.target.value}))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Entrez le nom exact de l'entreprise"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Clé API OpenAI
                    </label>
                    <input
                      type="password"
                      value={swotForm.apiKey}
                      onChange={(e) => setSwotForm(prev => ({...prev, apiKey: e.target.value}))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="sk-..."
                      required
                    />
                  </div>

                  <div className="bg-blue-50 p-4 rounded-lg">
                    <h4 className="font-medium text-blue-800 mb-2">Instructions:</h4>
                    <ul className="text-sm text-blue-700 space-y-1">
                      <li>1. Uploadez votre fichier CSV de profilage</li>
                      <li>2. Uploadez un ou plusieurs PDFs avec les Q&A détaillées</li>
                      <li>3. Entrez le nom de l'entreprise</li>
                      <li>4. Ajoutez votre clé API OpenAI</li>
                      <li>5. Cliquez sur Générer</li>
                    </ul>
                    <div className="mt-2 p-2 bg-blue-100 rounded">
                      <p className="text-xs text-blue-600">
                        💡 Vous pouvez uploader plusieurs PDFs pour une analyse plus complète. 
                        Tous les documents seront analysés ensemble.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <button
                type="submit"
                disabled={swotLoading || !swotForm.csvFile || swotForm.pdfFiles.length === 0 || !swotForm.businessName || !swotForm.apiKey}
                className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3 px-6 rounded-md font-medium hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                {swotLoading ? (
                  <>
                    <Loader2 className="animate-spin inline w-5 h-5 mr-2" />
                    Génération en cours...
                  </>
                ) : (
                  'Générer l\'Analyse SWOT'
                )}
              </button>
            </form>

            {/* SWOT Result */}
            {swotResult && (
              <div className="mt-8 space-y-6">
                {/* SWOT Analysis Results */}
                <div className="p-6 bg-green-50 border border-green-200 rounded-lg">
                  <div className="flex items-center mb-4">
                    <CheckCircle className="w-6 h-6 text-green-500 mr-2" />
                    <h3 className="text-lg font-semibold text-green-800">Analyse SWOT générée avec succès!</h3>
                  </div>
                  <div className="space-y-2 mb-4">
                    <p><strong>Entreprise:</strong> {swotResult.business_name}</p>
                    <p><strong>Fichiers analysés:</strong> {swotResult.files_count} PDF{swotResult.files_count > 1 ? 's' : ''}</p>
                    {swotResult.processed_files && (
                      <div>
                        <p><strong>Documents traités:</strong></p>
                        <ul className="list-disc list-inside text-sm text-gray-600 ml-4">
                          {swotResult.processed_files.map((filename, index) => (
                            <li key={index}>{filename}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                  
                  <div className="mb-6">
                    <h4 className="font-medium mb-3">Aperçu de l'analyse SWOT:</h4>
                    <div className="bg-white p-4 rounded-lg border max-h-96 overflow-y-auto">
                      <pre className="whitespace-pre-wrap text-sm text-gray-700">
                        {swotResult.swot_analysis}
                      </pre>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-3">
                    <button
                      onClick={() => downloadPdf(swotResult.pdf_id, `${swotResult.business_name}_analyse_SWOT.pdf`)}
                      className="bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 transition-colors"
                    >
                      <Download className="inline w-4 h-4 mr-2" />
                      Télécharger SWOT PDF
                    </button>
                    
                    <button
                      onClick={generateActionPlan}
                      disabled={actionPlanLoading}
                      className="bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {actionPlanLoading ? (
                        <>
                          <Loader2 className="animate-spin inline w-4 h-4 mr-2" />
                          Génération...
                        </>
                      ) : (
                        <>
                          <Target className="inline w-4 h-4 mr-2" />
                          Générer le Plan d'Action
                        </>
                      )}
                    </button>
                  </div>
                  
                  {!actionPlanResult && (
                    <div className="mt-3 p-3 bg-green-100 rounded-lg">
                      <p className="text-sm text-green-700">
                        ✅ <strong>SWOT terminé !</strong> Vous pouvez maintenant générer un plan d'action stratégique pour des recommandations concrètes.
                      </p>
                    </div>
                  )}
                </div>

                {/* Action Plan Results */}
                {actionPlanResult && (
                  <div className="p-6 bg-blue-50 border border-blue-200 rounded-lg">
                    <div className="flex items-center mb-4">
                      <CheckCircle className="w-6 h-6 text-blue-500 mr-2" />
                      <h3 className="text-lg font-semibold text-blue-800">Plan d'Action généré avec succès!</h3>
                    </div>
                    
                    <div className="space-y-2 mb-4">
                      <p><strong>Entreprise:</strong> {actionPlanResult.business_name}</p>
                      <p><strong>Basé sur:</strong> Analyse SWOT + {actionPlanResult.files_count} document{actionPlanResult.files_count > 1 ? 's' : ''} détaillé{actionPlanResult.files_count > 1 ? 's' : ''}</p>
                    </div>
                    
                    <div className="mb-6">
                      <h4 className="font-medium mb-3">Plan d'Action Stratégique:</h4>
                      <div className="bg-white p-4 rounded-lg border max-h-96 overflow-y-auto">
                        <pre className="whitespace-pre-wrap text-sm text-gray-700">
                          {actionPlanResult.action_plan}
                        </pre>
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-3 mb-4">
                      <button
                        onClick={() => downloadPdf(actionPlanResult.action_pdf_id, `${actionPlanResult.business_name}_plan_action.pdf`)}
                        className="bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 transition-colors"
                      >
                        <Download className="inline w-4 h-4 mr-2" />
                        Plan d'Action Seul (PDF)
                      </button>
                      
                      <button
                        onClick={() => downloadPdf(actionPlanResult.comprehensive_pdf_id, `${actionPlanResult.business_name}_strategie_complete.pdf`)}
                        className="bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 transition-colors"
                      >
                        <Download className="inline w-4 h-4 mr-2" />
                        Stratégie Complète (PDF)
                      </button>
                    </div>
                    
                    <div className="p-4 bg-blue-100 rounded-lg">
                      <p className="text-sm text-blue-700">
                        💡 <strong>Deux options de téléchargement :</strong>
                        <br />• <strong>SWOT Seul :</strong> Analyse SWOT uniquement
                        <br />• <strong>Stratégie Complète :</strong> SWOT + Plan d'action détaillé
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="bg-gray-800 text-white py-8 mt-16">
        <div className="max-w-6xl mx-auto px-4 text-center">
          <p className="text-lg font-semibold mb-2">AI Business Analysis Platform</p>
          <p className="text-gray-400">Propulsé par OpenAI GPT-4o • Développé avec FastAPI & React • Créer par Molly Ho</p>
        </div>
      </footer>
    </div>
  );
};

export default App;