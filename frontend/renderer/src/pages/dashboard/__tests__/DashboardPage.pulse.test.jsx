import React from 'react';
import { render, screen } from '@testing-library/react';
import DashboardPage from '../DashboardPage';

// Mock useApp to avoid context issues
jest.mock('../../../app/context/AppContext', () => ({
  useApp: () => ({
    user: { username: 'testuser' },
    apiOk: true,
    setPage: jest.fn(),
    setUploadHighlights: jest.fn(),
  }),
}));

describe('Upload button pulse effect', () => {
  it('shows pulse when no projects uploaded', () => {
    render(<DashboardPage />);
    // By default, stats.projects is '—' (no projects)
    const uploadButton = screen.getByRole('button', { name: /upload project/i });
    expect(uploadButton.className).toMatch(/upload-pulse/);
  });

  it('does not show pulse when projects exist', () => {
    // Patch React to set stats.projects to a nonzero value
    const React = require('react');
    const useState = React.useState;
    jest.spyOn(React, 'useState').mockImplementationOnce(() => [{
      projects: 2, skills: '—', experience: '—', resumes: '—'
    }, jest.fn()]);
    render(<DashboardPage />);
    const uploadButton = screen.getByRole('button', { name: /upload project/i });
    expect(uploadButton.className).not.toMatch(/upload-pulse/);
    React.useState.mockRestore();
  });
});
