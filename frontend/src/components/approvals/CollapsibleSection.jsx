import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { ChevronDown, ChevronRight } from 'lucide-react';

const CollapsibleSection = ({ title, icon: Icon, count, isDark, children, defaultOpen = true, testId }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  
  return (
    <Card className={`mb-6 ${isDark ? 'border-zinc-700 bg-zinc-800' : 'border-zinc-200'}`} data-testid={testId}>
      <CardHeader 
        className="pb-3 cursor-pointer select-none hover:bg-zinc-50/50 dark:hover:bg-zinc-700/30 transition-colors rounded-t-lg"
        onClick={() => setIsOpen(!isOpen)}
      >
        <CardTitle className={`text-base flex items-center gap-2 ${isDark ? 'text-zinc-100' : ''}`}>
          {Icon && <Icon className="w-5 h-5" />}
          {title}
          {count !== undefined && count > 0 && (
            <span className="text-xs px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 ml-1">
              {count}
            </span>
          )}
          <span className="ml-auto">
            {isOpen ? <ChevronDown className="w-4 h-4 text-zinc-400" /> : <ChevronRight className="w-4 h-4 text-zinc-400" />}
          </span>
        </CardTitle>
      </CardHeader>
      {isOpen && <CardContent>{children}</CardContent>}
    </Card>
  );
};

export default CollapsibleSection;
