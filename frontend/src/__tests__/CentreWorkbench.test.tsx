import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { CentreWorkbench } from '../components/CentreWorkbench';
import { AppMetadata } from '../types';

describe('CentreWorkbench Component', () => {
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
        name: 'Rental Workflow',
        document_type: 'Rental Vehicle',
        states: [
          { state: 'Draft', doc_status: 0, allow_edit: 'System Manager' },
          { state: 'Active', doc_status: 1, allow_edit: 'System Manager' },
        ],
        transitions: [
          { state: 'Draft', action: 'Activate', next_state: 'Active', allowed: 'System Manager' },
        ],
      },
    ],
  };

  it('renders ERD tab with doctype cards and fields', () => {
    render(<CentreWorkbench app={mockApp} />);

    expect(screen.getByText('Rental Vehicle')).toBeDefined();
    expect(screen.getByText('license_plate')).toBeDefined();
    expect(screen.getByText('daily_rate')).toBeDefined();
  });

  it('switches between tabs cleanly', () => {
    render(<CentreWorkbench app={mockApp} />);

    // Click Form Simulator tab
    const formTabBtn = screen.getByText('Form Simulator');
    fireEvent.click(formTabBtn);
    expect(screen.getByText('Simulate Form:')).toBeDefined();

    // Click Workflows tab
    const workflowTabBtn = screen.getByText('Workflows');
    fireEvent.click(workflowTabBtn);
    expect(screen.getByText('Rental Workflow')).toBeDefined();
    expect(screen.getAllByText('Draft').length).toBeGreaterThan(0);
  });
});
