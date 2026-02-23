// client/src/pages/HealthCheck.tsx
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, CheckCircle2 } from "lucide-react";

type HealthStatus = {
  service: string;
  status: "ok" | "error";
  message: string;
};

// This function calls the /api/health endpoint on your server
async function fetchHealthStatus(): Promise<{ checks: HealthStatus[] }> {
  const res = await fetch("/api/health");
  if (!res.ok) {
    throw new Error("Failed to fetch health status from the server.");
  }
  return res.json();
}

export function HealthCheckPage() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["healthCheck"],
    queryFn: fetchHealthStatus,
  });

  if (isLoading) {
    return (
      <div className="container mx-auto p-4">
        <p>Loading Health Status...</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="container mx-auto p-4">
        <p>Error: {error.message}</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      <Card>
        <CardHeader>
          <CardTitle>Application Health Check</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-4 text-muted-foreground">
            This page checks the connectivity between the web server and its
            backend services.
          </p>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[100px]">Status</TableHead>
                <TableHead>Service</TableHead>
                <TableHead>Details</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.checks.map((check) => (
                <TableRow key={check.service}>
                  <TableCell>
                    <Badge
                      variant={check.status === "ok" ? "default" : "destructive"}
                      className="flex items-center w-fit"
                    >
                      {check.status === "ok" ? (
                        <CheckCircle2 className="mr-1 h-4 w-4" />
                      ) : (
                        <AlertCircle className="mr-1 h-4 w-4" />
                      )}
                      {check.status.toUpperCase()}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-medium">{check.service}</TableCell>
                  <TableCell>{check.message}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

