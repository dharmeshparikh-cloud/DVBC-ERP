import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { API } from '../App';
import EmployeeFlowChart from './EmployeeFlowChart';

const EmployeeFlowPage = () => {
  const { employeeId } = useParams();

  const { data, isLoading, error } = useQuery({
    queryKey: ['employee-flow', employeeId],
    queryFn: async () => {
      const res = await axios.get(`${API}/employees/flow-status/${employeeId || 'me'}`);
      return res.data;
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px] text-red-500">
        Failed to load employee flow data
      </div>
    );
  }

  return <EmployeeFlowChart employeeData={data} />;
};

export default EmployeeFlowPage;
