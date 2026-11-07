import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  activateModel,
  deletePerson,
  getBootstrap,
  getJob,
  submitCollect,
  submitRecognition,
  submitTraining
} from "./api/client";
import type { Job, Model, Person, SourceKind, TaskKind } from "./api/types";
import { CameraPanel } from "./components/CameraPanel";
import { DatasetLedger } from "./components/DatasetLedger";
import { Footer } from "./components/Footer";
import { JobLedger } from "./components/JobLedger";
import { ModelLedger } from "./components/ModelLedger";
import { NavPill } from "./components/NavPill";
import { ResultCard } from "./components/ResultCard";
import { SampleManager } from "./components/SampleManager";
import { ScanStage } from "./components/ScanStage";
import { TaskConsole } from "./components/TaskConsole";
import { ToastNotice, type Notice } from "./components/ToastNotice";

const terminalStatuses = new Set(["succeeded", "failed", "interrupted"]);

export default function App() {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<TaskKind>("collect");
  const [source, setSource] = useState<SourceKind>("photo");
  const [person, setPerson] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [selectedModelId, setSelectedModelId] = useState("");
  const [activeJobId, setActiveJobId] = useState("");
  const [submitError, setSubmitError] = useState("");
  const [managingPerson, setManagingPerson] = useState<Person | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);

  const bootstrapQuery = useQuery({
    queryKey: ["bootstrap"],
    queryFn: getBootstrap
  });

  useEffect(() => {
    if (!selectedModelId && bootstrapQuery.data?.activeModelId) {
      setSelectedModelId(bootstrapQuery.data.activeModelId);
    }
  }, [bootstrapQuery.data?.activeModelId, selectedModelId]);

  useEffect(() => {
    setFiles([]);
    setSubmitError("");
  }, [mode, source]);

  const jobQuery = useQuery({
    queryKey: ["job", activeJobId],
    queryFn: () => getJob(activeJobId),
    enabled: Boolean(activeJobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && terminalStatuses.has(status) ? false : 700;
    }
  });

  useEffect(() => {
    const status = jobQuery.data?.status;
    if (status && terminalStatuses.has(status)) {
      void queryClient.invalidateQueries({ queryKey: ["bootstrap"] });
      if (jobQuery.data?.result?.modelId) {
        setSelectedModelId(String(jobQuery.data.result.modelId));
      }
    }
  }, [jobQuery.data, queryClient]);

  const showNotice = useCallback((message: string, tone: Notice["tone"] = "success") => {
    setNotice({ id: Date.now(), message, tone });
  }, []);
  const dismissNotice = useCallback(() => setNotice(null), []);

  const handleCameraStopped = useCallback(
    ({ saved, duplicates }: { saved: number; duplicates: number }) => {
      void queryClient.invalidateQueries({ queryKey: ["bootstrap"] });
      if (saved > 0) {
        showNotice(
          duplicates > 0
            ? `已自动保存 ${saved} 张人脸，并跳过 ${duplicates} 张重复样本。`
            : `已自动保存 ${saved} 张人脸，数据集统计已更新。`
        );
      } else if (duplicates > 0) {
        showNotice(`本次没有新增样本，已跳过 ${duplicates} 张重复人脸。`);
      } else {
        showNotice("采集已停止，本次没有检测到可保存的人脸。");
      }
    },
    [queryClient, showNotice]
  );

  const submitMutation = useMutation({
    mutationFn: async () => {
      if (mode === "collect") {
        if (source === "camera") {
          return null;
        }
        return submitCollect(person, source, files, 10, 200);
      }
      if (mode === "train") {
        return submitTraining({
          epochs: 8,
          batchSize: 20,
          threshold: bootstrapQuery.data?.threshold ?? 0.7,
          seed: 42
        });
      }
      if (source === "camera") {
        return null;
      }
      return submitRecognition(selectedModelId, source, files);
    },
    onMutate: () => setSubmitError(""),
    onSuccess: (job) => {
      if (job) {
        setActiveJobId(job.id);
        queryClient.setQueryData(["job", job.id], job);
      }
    },
    onError: (error) => {
      setSubmitError(error instanceof Error ? error.message : "任务提交失败");
    }
  });

  const activateMutation = useMutation({
    mutationFn: (model: Model) => activateModel(model.id),
    onSuccess: (model) => {
      setSelectedModelId(model.id);
      void queryClient.invalidateQueries({ queryKey: ["bootstrap"] });
    },
    onError: (error) => {
      setSubmitError(error instanceof Error ? error.message : "模型启用失败");
    }
  });

  const jobs = useMemo(() => {
    const recent = bootstrapQuery.data?.recentJobs ?? [];
    const active = jobQuery.data;
    if (!active) {
      return recent;
    }
    return [active, ...recent.filter((job: Job) => job.id !== active.id)];
  }, [bootstrapQuery.data?.recentJobs, jobQuery.data]);

  function startCollect() {
    setMode("collect");
    setSource("photo");
    document.getElementById("workbench")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function continueCollection(person: Person) {
    setPerson(person.name);
    setMode("collect");
    setSource("camera");
    document.getElementById("workbench")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function removePerson(person: Person) {
    const confirmed = window.confirm(
      `确认删除“${person.name}”及其 ${person.sampleCount} 张人脸样本？已训练模型不会自动删除，此操作不可恢复。`
    );
    if (!confirmed) {
      return;
    }
    try {
      const result = await deletePerson(person.id);
      setManagingPerson((current) => (current?.id === person.id ? null : current));
      setPerson((current) => (current === person.name ? "" : current));
      await queryClient.invalidateQueries({ queryKey: ["bootstrap"] });
      showNotice(`已删除“${person.name}”及 ${result.removedFaces} 张人脸样本。`);
    } catch (error) {
      showNotice(error instanceof Error ? error.message : "删除人物失败", "error");
    }
  }

  if (bootstrapQuery.isPending) {
    return (
      <main className="boot-state" aria-live="polite">
        <span className="boot-state__mark" aria-hidden="true" />
        正在连接本地推理引擎…
      </main>
    );
  }

  if (bootstrapQuery.isError || !bootstrapQuery.data) {
    return (
      <main className="boot-state boot-state--error" role="alert">
        无法连接 Face Workbench 后端。请确认 `python main.py` 已启动，然后刷新页面。
      </main>
    );
  }

  const bootstrap = bootstrapQuery.data;
  const activeJob = jobQuery.data ?? null;
  const cameraPanel =
    source === "camera" && mode !== "train" ? (
      <CameraPanel
        mode={mode}
        person={person}
        modelId={selectedModelId}
        maxEdge={bootstrap.cameraFrameEdge}
        onCollectionStopped={handleCameraStopped}
      />
    ) : null;

  return (
    <div className="app-shell" id="top">
      <div className="atmosphere" aria-hidden="true" />
      <NavPill engineReady={bootstrap.engineReady} onStart={startCollect} />

      <main>
        <header className="hero">
          <div className="hero__copy">
            <span className="hero__mark mono">FACE WORKBENCH / LOCAL FIRST</span>
            <h1>从采集到识别，一条完整链路。</h1>
            <p>
              从照片、视频或摄像头收集人脸，训练轻量 CNN，再把同一个模型带回三种识别场景。
            </p>
          </div>
          <div className="hero__signal" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
        </header>

        <section className="workbench" id="workbench" aria-label="人脸识别工作台">
          <ScanStage mode={mode} files={files} activeJob={activeJob}>
            {cameraPanel}
          </ScanStage>
          <TaskConsole
            bootstrap={bootstrap}
            mode={mode}
            source={source}
            person={person}
            files={files}
            selectedModelId={selectedModelId}
            busy={submitMutation.isPending}
            error={submitError || (jobQuery.data?.status === "failed" ? jobQuery.data.errorMessage ?? "任务失败" : "")}
            onModeChange={setMode}
            onSourceChange={setSource}
            onPersonChange={setPerson}
            onFilesChange={setFiles}
            onModelChange={setSelectedModelId}
            onSubmit={() => submitMutation.mutate()}
            onActivateModel={(model) => activateMutation.mutate(model)}
          />
        </section>

        {activeJob?.status === "succeeded" && <ResultCard job={activeJob} />}

        <div className="ledger-grid">
          <DatasetLedger
            bootstrap={bootstrap}
            onStart={startCollect}
            onContinue={continueCollection}
            onManage={setManagingPerson}
            onDelete={(person) => void removePerson(person)}
          />
          <ModelLedger
            bootstrap={bootstrap}
            onActivate={(model) => activateMutation.mutate(model)}
          />
        </div>
        <JobLedger jobs={jobs} />
      </main>

      <Footer />
      {managingPerson && (
        <SampleManager
          person={managingPerson}
          onClose={() => setManagingPerson(null)}
          onChanged={(message) => showNotice(message)}
          onError={(message) => showNotice(message, "error")}
        />
      )}
      {notice && <ToastNotice notice={notice} onDismiss={dismissNotice} />}
    </div>
  );
}
