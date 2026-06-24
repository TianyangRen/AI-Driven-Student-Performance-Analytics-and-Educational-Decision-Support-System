import client from './client';

export const login = (username, password) =>
  client.post('/auth/login', { username, password }).then((r) => r.data);

export const register = (payload) =>
  client.post('/auth/register', payload).then((r) => r.data);

export const logout = () => client.post('/auth/logout').then((r) => r.data);

export const fetchMe = () => client.get('/auth/me').then((r) => r.data);
