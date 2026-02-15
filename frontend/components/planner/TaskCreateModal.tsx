"use client";

import { useEffect, useState } from "react";
import { X, Loader2 } from "lucide-react";
import { createTask, fetchBuckets, type PlannerBucket } from "@/lib/congressTwinApi";
import { usePlanId } from "./PlanContext";

interface TaskCreateModalProps {
  onClose: () => void;
  onCreated?: () => void;
}

export default function TaskCreateModal({ onClose, onCreated }: TaskCreateModalProps) {
  const planId = usePlanId();
  const [buckets, setBuckets] = useState<PlannerBucket[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [bucketId, setBucketId] = useState("");
  const [dueDateTime, setDueDateTime] = useState("");
  const [startDateTime, setStartDateTime] = useState("");
  const [description, setDescription] = useState("");

  useEffect(() => {
    fetchBuckets(planId)
      .then((r) => {
        setBuckets(r.buckets);
        if (r.buckets.length && !bucketId) setBucketId(r.buckets[0].id);
      })
      .catch(() => setBuckets([]));
  }, [planId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !bucketId) {
      setError("Title and bucket are required");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const toIso = (s: string) => (s ? (s.endsWith("Z") || s.includes("+") ? s : `${s}Z`) : undefined);
      await createTask(planId, {
        title: title.trim(),
        bucketId,
        dueDateTime: toIso(dueDateTime),
        startDateTime: toIso(startDateTime),
        description: description.trim() || undefined,
      });
      onCreated?.();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create task");
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div className="fixed inset-0 bg-black/30 z-40" aria-hidden onClick={onClose} />
      <div className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-md bg-white rounded-xl shadow-xl">
        <div className="flex items-center justify-between p-4 border-b border-[#e5e7eb]">
          <h2 className="text-lg font-bold text-[#111827]">Create task</h2>
          <button type="button" onClick={onClose} className="rounded p-1.5 text-[#6b7280] hover:bg-[#f3f4f6]">
            <X className="h-5 w-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>
          )}
          <div>
            <label className="block text-sm font-medium text-[#374151] mb-1">Title *</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full rounded-lg border border-[#d1d5db] px-3 py-2 text-sm focus:ring-2 focus:ring-[#16a34a] focus:border-[#16a34a]"
              placeholder="Task title"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[#374151] mb-1">Bucket *</label>
            <select
              value={bucketId}
              onChange={(e) => setBucketId(e.target.value)}
              className="w-full rounded-lg border border-[#d1d5db] px-3 py-2 text-sm focus:ring-2 focus:ring-[#16a34a] focus:border-[#16a34a]"
            >
              {buckets.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-[#374151] mb-1">Start date</label>
              <input
                type="datetime-local"
                value={startDateTime}
                onChange={(e) => setStartDateTime(e.target.value)}
                className="w-full rounded-lg border border-[#d1d5db] px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#374151] mb-1">Due date</label>
              <input
                type="datetime-local"
                value={dueDateTime}
                onChange={(e) => setDueDateTime(e.target.value)}
                className="w-full rounded-lg border border-[#d1d5db] px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-[#374151] mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full rounded-lg border border-[#d1d5db] px-3 py-2 text-sm resize-none"
              placeholder="Optional description"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-[#6b7280] hover:bg-[#f3f4f6] rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-[#16a34a] rounded-lg hover:bg-[#15803d] disabled:opacity-60"
            >
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Create task
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
