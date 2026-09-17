import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { api } from '../../api/client';
import { 
  FileCheck, 
  CheckCircle2, 
  AlertCircle, 
  ArrowLeft, 
  Send,
  Clock,
  Sparkles
} from 'lucide-react';
import { Questionnaire, Question, QuestionnaireResponse } from '../../types';

export const QuestionnairePage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const appointmentId = searchParams.get('appointment_id');

  const [questionnaire, setQuestionnaire] = useState<Questionnaire | null>(null);
  const [existingResponse, setExistingResponse] = useState<QuestionnaireResponse | null>(null);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      if (!appointmentId) {
        setError('No appointment ID provided. Please navigate from your appointments list.');
        setLoading(false);
        return;
      }

      try {
        const data = await api.getQuestionnaireForAppointment(appointmentId);
        setQuestionnaire(data.questionnaire);
        if (data.response) {
          setExistingResponse(data.response);
          setAnswers(data.response.answers);
        } else {
          // Initialize defaults
          const initial: Record<string, any> = {};
          data.questionnaire.questions.forEach((q) => {
            if (q.question_type === 'NUMERIC') initial[q.id] = 5;
            else if (q.question_type === 'YES_NO') initial[q.id] = 'No';
            else initial[q.id] = '';
          });
          setAnswers(initial);
        }
      } catch (err: any) {
        setError(err.message || 'Failed to load questionnaire.');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [appointmentId]);

  const handleInputChange = (questionId: string, value: any) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!appointmentId) return;

    setSubmitting(true);
    setError(null);
    try {
      const res = await api.submitQuestionnaireResponse(appointmentId, answers);
      setSuccessMessage(res.message);
      setExistingResponse({
        id: 'new-response',
        status: 'COMPLETED',
        answers,
        completed_at: res.completed_at,
      });
    } catch (err: any) {
      setError(err.message || 'Failed to submit questionnaire.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12 flex flex-col items-center justify-center">
        <div className="h-8 w-8 border-3 border-teal-600 border-t-transparent rounded-full animate-spin mb-3" />
        <p className="text-slate-600 text-sm">Loading pre-visit questionnaire...</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 sm:px-6">
      {/* Back link */}
      <button
        onClick={() => navigate(-1)}
        className="flex items-center space-x-1 text-sm font-medium text-slate-500 hover:text-slate-800 mb-6 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        <span>Back to Appointments</span>
      </button>

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-start space-x-3">
          <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5 text-rose-600" />
          <div>{error}</div>
        </div>
      )}

      {successMessage && (
        <div className="mb-6 p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-sm flex items-center space-x-3 shadow-xs">
          <CheckCircle2 className="h-5 w-5 text-emerald-600 flex-shrink-0" />
          <div className="font-medium">{successMessage} Your doctor has been notified.</div>
        </div>
      )}

      {questionnaire && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          {/* Header */}
          <div className="p-6 border-b border-slate-200 bg-gradient-to-r from-teal-50 to-emerald-50">
            <div className="flex items-center space-x-2 text-teal-800 text-xs font-bold uppercase tracking-wider mb-1">
              <FileCheck className="h-4 w-4" />
              <span>Pre-Visit Clinical Intake</span>
            </div>
            <h1 className="text-xl font-bold text-slate-900">{questionnaire.title}</h1>
            {questionnaire.description && (
              <p className="text-sm text-slate-600 mt-1">{questionnaire.description}</p>
            )}

            {existingResponse?.completed_at && (
              <div className="mt-3 inline-flex items-center space-x-1.5 text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>Completed on {new Date(existingResponse.completed_at).toLocaleString()}</span>
              </div>
            )}
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="p-6 space-y-6">
            {questionnaire.questions.map((q: Question, idx: number) => (
              <div key={q.id} className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
                <label className="block text-sm font-semibold text-slate-900 mb-2">
                  <span className="text-teal-700 font-bold mr-1">{idx + 1}.</span>
                  {q.prompt}
                  {q.is_required && <span className="text-rose-500 ml-1">*</span>}
                </label>

                {/* Multiple / Single Choice */}
                {q.question_type === 'CHOICE' && q.options && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
                    {q.options.map((opt) => (
                      <label
                        key={opt}
                        className={`flex items-center space-x-2.5 p-3 rounded-lg border text-sm cursor-pointer transition-all ${
                          answers[q.id] === opt
                            ? 'bg-teal-50 border-teal-500 text-teal-900 font-medium'
                            : 'bg-white border-slate-200 text-slate-700 hover:border-slate-300'
                        }`}
                      >
                        <input
                          type="radio"
                          name={q.id}
                          value={opt}
                          checked={answers[q.id] === opt}
                          onChange={() => handleInputChange(q.id, opt)}
                          className="text-teal-600 focus:ring-teal-500"
                        />
                        <span>{opt}</span>
                      </label>
                    ))}
                  </div>
                )}

                {/* Numeric Scale 1-10 */}
                {q.question_type === 'NUMERIC' && (
                  <div className="space-y-3 mt-2">
                    <div className="flex justify-between items-center text-xs text-slate-500 font-medium">
                      <span>1 (Mild / Barely Noticeable)</span>
                      <span className="text-base font-bold text-teal-700 bg-teal-50 px-3 py-0.5 rounded-full border border-teal-200">
                        Level: {answers[q.id] ?? 5} / 10
                      </span>
                      <span>10 (Severe / Debilitating)</span>
                    </div>
                    <input
                      type="range"
                      min="1"
                      max="10"
                      value={answers[q.id] ?? 5}
                      onChange={(e) => handleInputChange(q.id, parseInt(e.target.value))}
                      className="w-full accent-teal-600 h-2 bg-slate-200 rounded-lg cursor-pointer"
                    />
                  </div>
                )}

                {/* YES/NO Toggle */}
                {q.question_type === 'YES_NO' && (
                  <div className="flex space-x-3 mt-2">
                    {['Yes', 'No'].map((val) => (
                      <button
                        type="button"
                        key={val}
                        onClick={() => handleInputChange(q.id, val)}
                        className={`px-5 py-2 rounded-xl text-sm font-semibold border transition-all ${
                          answers[q.id] === val
                            ? 'bg-teal-600 text-white border-teal-600 shadow-xs'
                            : 'bg-white text-slate-700 border-slate-200 hover:border-slate-300'
                        }`}
                      >
                        {val}
                      </button>
                    ))}
                  </div>
                )}

                {/* Short Text */}
                {q.question_type === 'SHORT_TEXT' && (
                  <input
                    type="text"
                    value={answers[q.id] || ''}
                    onChange={(e) => handleInputChange(q.id, e.target.value)}
                    placeholder="e.g. Approximately 3 weeks, started after playing tennis"
                    required={q.is_required}
                    className="w-full mt-2 px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                  />
                )}
              </div>
            ))}

            {/* Submit CTA */}
            <div className="pt-4 flex justify-end">
              <button
                type="submit"
                disabled={submitting}
                className="px-6 py-2.5 bg-teal-600 hover:bg-teal-700 text-white rounded-xl font-semibold text-sm shadow-sm transition-all flex items-center space-x-2 disabled:opacity-50"
              >
                {submitting ? (
                  <>
                    <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Saving Intake...</span>
                  </>
                ) : (
                  <>
                    <span>{existingResponse ? 'Update Intake Answers' : 'Submit Intake to Physician'}</span>
                    <Send className="h-4 w-4" />
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
