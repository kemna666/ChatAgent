import { useEffect, useState } from 'react';
import { FiGlobe, FiSettings, FiX } from 'react-icons/fi';
import { useLanguage } from '../contexts/LanguageContext';
import { Language } from '../i18n/translations';

export default function GlobalSettings() {
  const [open, setOpen] = useState(false);
  const { language, setLanguage, t } = useLanguage();

  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open]);

  const languageOptions: Array<{ value: Language; label: string }> = [
    { value: 'zh', label: t('languageChinese') },
    { value: 'en', label: t('languageEnglish') },
  ];
  const currentLanguageLabel = language === 'zh' ? t('languageChinese') : t('languageEnglish');

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-5 left-5 z-40 flex items-center gap-2 rounded-full border border-gray-200 bg-white px-4 py-3 text-sm font-medium text-gray-700 shadow-lg transition hover:border-gray-300 hover:text-gray-900"
        title={t('settingsButton')}
      >
        <FiSettings size={16} />
        <span>{t('settingsButton')}</span>
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-950/45 px-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-gray-200 bg-white p-6 shadow-2xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  {t('settingsTitle')}
                </h2>
                <p className="mt-2 text-sm leading-6 text-gray-600">
                  {t('settingsSubtitle')}
                </p>
              </div>
              <button
                onClick={() => setOpen(false)}
                className="rounded-full p-2 text-gray-500 transition hover:bg-gray-100 hover:text-gray-800"
                title={t('close')}
              >
                <FiX size={18} />
              </button>
            </div>

            <div className="mt-6 rounded-2xl border border-gray-200 bg-gray-50 p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100 text-blue-600">
                  <FiGlobe size={18} />
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-900">
                    {t('languageLabel')}
                  </p>
                  <p className="text-xs text-gray-500">
                    {t('currentLanguage', { language: currentLanguageLabel })}
                  </p>
                </div>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-3">
                {languageOptions.map((option) => {
                  const selected = language === option.value;
                  return (
                    <button
                      key={option.value}
                      onClick={() => setLanguage(option.value)}
                      className={`rounded-xl border px-4 py-3 text-sm font-medium transition ${
                        selected
                          ? 'border-blue-500 bg-blue-500 text-white shadow-sm'
                          : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:text-gray-900'
                      }`}
                    >
                      {option.label}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setOpen(false)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition hover:border-gray-400 hover:text-gray-900"
              >
                {t('close')}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
