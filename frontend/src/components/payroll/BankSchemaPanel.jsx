/**
 * BankSchemaPanel.jsx
 * 
 * Component to display bank details schema status and trigger migration
 * to standardized format.
 */

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Alert, AlertDescription } from '../ui/alert';
import { 
  CheckCircle2, AlertTriangle, Database, RefreshCw, Loader2, 
  CreditCard, Building2, Hash
} from 'lucide-react';
import { toast } from 'sonner';

const BankSchemaPanel = ({ API, authHeaders }) => {
  const queryClient = useQueryClient();
  const [migrating, setMigrating] = useState(false);

  // Fetch bank schema status
  const { data: schemaStatus, isLoading, refetch } = useQuery({
    queryKey: ['bank-schema-status'],
    queryFn: async () => {
      const response = await axios.get(`${API}/payroll/bank-schema-status`, authHeaders);
      return response.data;
    },
    staleTime: 2 * 60 * 1000,
  });

  // Fetch employees with incomplete bank details
  const { data: bankStatus } = useQuery({
    queryKey: ['employees-bank-status'],
    queryFn: async () => {
      const response = await axios.get(`${API}/payroll/employees-bank-status`, authHeaders);
      return response.data;
    },
    staleTime: 2 * 60 * 1000,
  });

  // Mutation for bulk standardization
  const handleBulkStandardize = async () => {
    try {
      setMigrating(true);
      const response = await axios.post(
        `${API}/payroll/standardize-bank-details-bulk`,
        {},
        authHeaders
      );
      toast.success(`Migration complete: ${response.data.migrated} employees updated`);
      refetch();
      queryClient.invalidateQueries({ queryKey: ['employees-bank-status'] });
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Migration failed');
    } finally {
      setMigrating(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-40">
        <Loader2 className="w-6 h-6 animate-spin text-zinc-400" />
      </div>
    );
  }

  const isStandardized = schemaStatus?.is_standardized;

  return (
    <div className="space-y-6" data-testid="bank-schema-panel">
      {/* Status Alert */}
      {isStandardized ? (
        <Alert className="border-emerald-200 bg-emerald-50">
          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          <AlertDescription className="text-emerald-800">
            <strong>Schema Standardized</strong> - All employee bank details are using the new nested format.
          </AlertDescription>
        </Alert>
      ) : (
        <Alert className="border-amber-200 bg-amber-50">
          <AlertTriangle className="h-4 w-4 text-amber-600" />
          <AlertDescription className="text-amber-800">
            <strong>{schemaStatus?.old_format_count} employees</strong> are using the old bank details format. 
            Run migration to standardize.
          </AlertDescription>
        </Alert>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="border-zinc-200">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-100">
                <Database className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <div className="text-xs text-zinc-500 uppercase tracking-wide">Old Format</div>
                <div className="text-2xl font-semibold">{schemaStatus?.old_format_count || 0}</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-200">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-emerald-100">
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <div className="text-xs text-zinc-500 uppercase tracking-wide">New Format</div>
                <div className="text-2xl font-semibold">{schemaStatus?.new_format_count || 0}</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-200">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-zinc-100">
                <CreditCard className="w-5 h-5 text-zinc-600" />
              </div>
              <div>
                <div className="text-xs text-zinc-500 uppercase tracking-wide">Total Active</div>
                <div className="text-2xl font-semibold">{schemaStatus?.total_active_employees || 0}</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Bank Details Completeness */}
      {bankStatus && (
        <Card className="border-zinc-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <CreditCard className="w-4 h-4" />
              Bank Details Completeness
            </CardTitle>
            <CardDescription>
              Status of bank information for active employees
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-zinc-50 rounded-lg">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                <span className="font-medium">Complete Bank Details</span>
              </div>
              <Badge className="bg-emerald-100 text-emerald-700">
                {bankStatus.complete_count} employees
              </Badge>
            </div>

            <div className="flex items-center justify-between p-3 bg-zinc-50 rounded-lg">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                <span className="font-medium">Incomplete Bank Details</span>
              </div>
              <Badge className="bg-amber-100 text-amber-700">
                {bankStatus.incomplete_count} employees
              </Badge>
            </div>

            {bankStatus.incomplete_count > 0 && bankStatus.incomplete_employees?.length > 0 && (
              <div className="mt-4">
                <div className="text-sm font-medium text-zinc-700 mb-2">Employees with missing details:</div>
                <div className="space-y-2">
                  {bankStatus.incomplete_(employees || []).map((emp, idx) => (
                    <div key={idx} className="flex items-center justify-between p-2 border border-zinc-200 rounded">
                      <div>
                        <span className="font-medium">{emp.employee_code}</span>
                        <span className="text-zinc-500 ml-2">{emp.name}</span>
                      </div>
                      <div className="flex gap-2">
                        {!emp.has_account && <Badge variant="outline" className="text-xs">No Account</Badge>}
                        {!emp.has_bank_name && <Badge variant="outline" className="text-xs">No Bank</Badge>}
                        {!emp.has_ifsc && <Badge variant="outline" className="text-xs">No IFSC</Badge>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Schema Format Explanation */}
      <Card className="border-zinc-200">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Schema Format</CardTitle>
          <CardDescription>
            Bank details should be stored in a standardized nested format
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Old Format */}
            <div className="p-4 border border-red-200 bg-red-50 rounded-lg">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="w-4 h-4 text-red-500" />
                <span className="font-medium text-red-700">Old Format (Deprecated)</span>
              </div>
              <pre className="text-xs bg-white p-3 rounded border border-red-200 overflow-x-auto">
{`{
  "bank_account_number": "1234...",
  "bank_name": "HDFC Bank",
  "ifsc_code": "HDFC0001234"
}`}
              </pre>
            </div>

            {/* New Format */}
            <div className="p-4 border border-emerald-200 bg-emerald-50 rounded-lg">
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span className="font-medium text-emerald-700">New Format (Standard)</span>
              </div>
              <pre className="text-xs bg-white p-3 rounded border border-emerald-200 overflow-x-auto">
{`{
  "bank_details": {
    "account_number": "1234...",
    "bank_name": "HDFC Bank",
    "ifsc_code": "HDFC0001234",
    "account_type": "savings",
    "branch": "Main Branch"
  }
}`}
              </pre>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Migration Action */}
      {!isStandardized && schemaStatus?.old_format_count > 0 && (
        <Card className="border-amber-200 bg-amber-50">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium text-amber-800">Migration Required</div>
                <div className="text-sm text-amber-600">
                  {schemaStatus.old_format_count} employees need to be migrated to the new format
                </div>
              </div>
              <Button 
                onClick={handleBulkStandardize}
                disabled={migrating}
                className="bg-amber-600 hover:bg-amber-700 text-white"
                data-testid="run-migration-btn"
              >
                {migrating ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    Migrating...
                  </>
                ) : (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Run Migration
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Old Format Samples */}
      {schemaStatus?.old_format_samples?.length > 0 && (
        <Card className="border-zinc-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Employees Using Old Format</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {(schemaStatus?.old_format_samples || []).map((emp, idx) => (
                <div key={idx} className="flex items-center justify-between p-2 bg-zinc-50 rounded">
                  <div>
                    <span className="font-medium">{emp.employee_id}</span>
                    <span className="text-zinc-500 ml-2">
                      {emp.first_name} {emp.last_name}
                    </span>
                  </div>
                  <Badge variant="outline" className="text-amber-600 border-amber-300">
                    Old Format
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default BankSchemaPanel;
