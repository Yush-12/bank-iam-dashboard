import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { randomizeData, uploadCustomData } from "../api/client";

const sampleSchema = {
  users: [
    {
      name: "John Doe",
      employee_id: "EMP1234",
      department: "Finance",
      job_title: "Analyst",
      status: "active",
      last_login_days_ago: 5,
      roles: ["Teller", "Payment Ops"]
    }
  ]
};

export default function Settings() {
  const queryClient = useQueryClient();
  const [file, setFile] = useState(null);
  const [uploadMessage, setUploadMessage] = useState("");

  const randomizeMutation = useMutation({
    mutationFn: randomizeData,
    onSuccess: async () => {
      await queryClient.invalidateQueries();
      setUploadMessage("Data randomized successfully!");
      setTimeout(() => setUploadMessage(""), 3000);
    },
    onError: (error) => {
      setUploadMessage(`Error: ${error.message}`);
    }
  });

  const uploadMutation = useMutation({
    mutationFn: uploadCustomData,
    onSuccess: async () => {
      await queryClient.invalidateQueries();
      setUploadMessage("Custom data uploaded successfully!");
      setFile(null);
      setTimeout(() => setUploadMessage(""), 3000);
    },
    onError: (error) => {
      setUploadMessage(`Upload failed: ${error.message}`);
    }
  });

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = () => {
    if (!file) return;
    uploadMutation.mutate(file);
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-lg font-semibold text-slate-100">Data Management</h2>
        <p className="text-sm text-slate-400">Manage the underlying mock dataset used by the compliance engine.</p>
      </div>

      {uploadMessage && (
        <div className={`p-4 rounded-lg text-sm font-medium ${uploadMessage.includes('Error') || uploadMessage.includes('failed') ? 'bg-red-500/10 text-red-400 border border-red-500/20' : 'bg-green-500/10 text-green-400 border border-green-500/20'}`}>
          {uploadMessage}
        </div>
      )}

      <section className="card p-6 border-bankBorder">
        <h3 className="text-base font-semibold text-slate-100 mb-2">Randomize Data</h3>
        <p className="text-sm text-slate-400 mb-4">
          Replace the current users and role assignments with a newly generated, randomized set. This will instantly update the dashboard and all violation findings.
        </p>
        <button
          type="button"
          onClick={() => randomizeMutation.mutate()}
          disabled={randomizeMutation.isPending || uploadMutation.isPending}
          className="inline-flex items-center gap-2 rounded-lg bg-bankPrimary px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-bankPrimary/20 transition-all hover:bg-bankAccent disabled:opacity-60"
        >
          {randomizeMutation.isPending && <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />}
          Generate Random Data
        </button>
      </section>

      <section className="card p-6 border-bankBorder">
        <div className="flex items-center gap-2 mb-2">
          <h3 className="text-base font-semibold text-slate-100">Upload Custom Data</h3>
          <div className="group relative">
            <div className="flex h-5 w-5 cursor-help items-center justify-center rounded-full bg-slate-800 text-xs font-bold text-slate-300 border border-bankBorder hover:bg-slate-700">
              !
            </div>
            {/* Tooltip Popup */}
            <div className="absolute left-8 -top-2 z-10 hidden w-96 rounded-xl border border-bankBorder bg-slate-900/95 p-4 shadow-xl backdrop-blur-sm group-hover:block">
              <h4 className="mb-2 text-sm font-semibold text-slate-100">Expected JSON Schema</h4>
              <p className="mb-3 text-xs text-slate-400">
                Upload a JSON file containing a <code className="text-bankPrimary">users</code> array. Roles must match exactly the names defined in the system.
              </p>
              <pre className="overflow-x-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-300 border border-slate-800">
                {JSON.stringify(sampleSchema, null, 2)}
              </pre>
            </div>
          </div>
        </div>
        <p className="text-sm text-slate-400 mb-4">
          Upload your own JSON dataset to see how the engine evaluates custom user and role configurations.
        </p>

        <div className="flex items-center gap-4">
          <input
            type="file"
            accept=".json"
            onChange={handleFileChange}
            className="block w-full max-w-sm text-sm text-slate-400 file:mr-4 file:rounded-lg file:border-0 file:bg-slate-800 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-slate-100 hover:file:bg-slate-700 cursor-pointer"
          />
          <button
            type="button"
            onClick={handleUpload}
            disabled={!file || uploadMutation.isPending || randomizeMutation.isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-slate-800 border border-bankBorder px-4 py-2 text-sm font-semibold text-slate-100 transition-all hover:bg-slate-700 disabled:opacity-50"
          >
            {uploadMutation.isPending && <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-100 border-t-transparent" />}
            Upload JSON
          </button>
        </div>
      </section>
    </div>
  );
}
