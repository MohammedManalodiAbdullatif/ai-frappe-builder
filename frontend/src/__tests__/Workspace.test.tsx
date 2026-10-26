import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { Workspace } from '../components/workspace/Workspace';
import { AppMetadata } from '../types';

beforeEach(() => {
  (globalThis as any).ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
});

describe('Workspace Component', () => {
  const mockApp: AppMetadata = {
    app_name: 'car_rental',
    title: 'Car Rental',
    modules: ['Fleet'],
    doctypes: [
      {
        name: 'Rental Vehicle',
        module: 'Fleet',
        fields: [
          { fieldname: 'license_plate', label: 'License Plate', fieldtype: 'Data', reqd: true },
          { fieldname: 'daily_rate', label: 'Daily Rate', fieldtype: 'Currency' },
        ],
        permissions: [
          { role: 'System Manager', read: true, write: true, create: true, delete: true },
        ],
      },
    ],
    workflows: [
      {
        name: 'Rental Approval',
        document_type: 'Rental Vehicle',
        states: [
          { state: 'Draft', doc_status: 0, allow_edit: 'System Manager' },
          { state: 'Active', doc_status: 1, allow_edit: 'System Manager' },
        ],
        transitions: [
          { state: 'Draft', action: 'Submit', next_state: 'Active', allowed: 'System Manager' },
        ],
      },
    ],
  };

  it('renders tabs and status bar with real values', () => {
    render(
      <Workspace
        isOpen={true}
        onClose={vi.fn()}
        app={mockApp}
        specRaw={{ app: mockApp }}
        sessionId="test-session"
        stage="discovery"
        validation={null}
      />
    );

    expect(screen.getByText('Data model')).toBeDefined();
    expect(screen.getByText('Forms')).toBeDefined();
    expect(screen.getByText('Workflows')).toBeDefined();
    expect(screen.getByText('Files')).toBeDefined();
    expect(screen.getByText('Spec')).toBeDefined();

    // In discovery stage with no validation yet:
    expect(screen.getAllByText('—').length).toBeGreaterThan(0);

    // Download button must be disabled until stage is Ready (done)
    const downloadBtn = screen.getByText('Download .zip').closest('button');
    expect(downloadBtn?.disabled).toBe(true);
  });

  it('switches to forms and workflows tabs correctly', () => {
    render(
      <Workspace
        isOpen={true}
        onClose={vi.fn()}
        app={mockApp}
        specRaw={{ app: mockApp }}
        sessionId="test-session"
        stage="done"
        validation={{ is_valid: true, errors: [], warnings: [], fix_hints: [] }}
        qaReport={{ execution_mode: 'static_only', passed: false }}
      />
    );

    // Switch to Workflows
    fireEvent.click(screen.getByText('Workflows'));
    expect(screen.getByText('Rental Approval')).toBeDefined();
    expect(screen.getAllByText('Draft').length).toBeGreaterThan(0);

    // In ready stage with validation run:
    expect(screen.getByText('Valid')).toBeDefined();
    expect(screen.getByText('static-only')).toBeDefined();
    const downloadBtn = screen.getByText('Download .zip').closest('button');
    expect(downloadBtn?.disabled).toBe(false);
  });
});
