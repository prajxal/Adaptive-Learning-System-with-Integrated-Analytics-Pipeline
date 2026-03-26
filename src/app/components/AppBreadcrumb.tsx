import React from "react";
import { Link } from "react-router-dom";
import {
  Breadcrumb,
  BreadcrumbList,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "./ui/breadcrumb";

export interface BreadcrumbSegment {
  label: string;
  href?: string; // If omitted, renders as current page (non-linked)
}

interface AppBreadcrumbProps {
  segments: BreadcrumbSegment[];
}

export default function AppBreadcrumb({ segments }: AppBreadcrumbProps) {
  return (
    <Breadcrumb className="mb-6">
      <BreadcrumbList>
        {segments.map((seg, i) => {
          const isLast = i === segments.length - 1;
          return (
            <React.Fragment key={i}>
              <BreadcrumbItem>
                {isLast || !seg.href ? (
                  <BreadcrumbPage
                    className="text-sm"
                    style={{ color: "var(--text-primary, #f1f5f9)" }}
                  >
                    {seg.label}
                  </BreadcrumbPage>
                ) : (
                  <BreadcrumbLink
                    asChild
                    className="text-sm"
                    style={{ color: "var(--text-muted, #64748b)" }}
                  >
                    <Link to={seg.href}>{seg.label}</Link>
                  </BreadcrumbLink>
                )}
              </BreadcrumbItem>
              {!isLast && <BreadcrumbSeparator />}
            </React.Fragment>
          );
        })}
      </BreadcrumbList>
    </Breadcrumb>
  );
}
