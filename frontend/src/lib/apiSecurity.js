import axios from 'axios';

axios.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('eovAccessToken');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !error.config?.url?.includes('/auth/login')) {
      sessionStorage.removeItem('eovAccessToken');
      window.dispatchEvent(new CustomEvent('eov:session-expired'));
    }
    return Promise.reject(error);
  },
);
