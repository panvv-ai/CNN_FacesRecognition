import { ArrowUpRight } from "lucide-react";

import { BrandMark } from "./BrandMark";

interface NavPillProps {
  engineReady: boolean;
  onStart: () => void;
}

export function NavPill({ engineReady, onStart }: NavPillProps) {
  return (
    <nav className="nav-pill" aria-label="主要导航">
      <a href="#top" className="nav-pill__brand" aria-label="Face Workbench 首页">
        <BrandMark />
      </a>
      <div className="nav-pill__links">
        <a href="#workbench">工作台</a>
        <a href="#dataset">数据</a>
        <a href="#models">模型</a>
      </div>
      <div className="nav-pill__status">
        <span className="status-light" data-ready={engineReady} aria-hidden="true" />
        <span>{engineReady ? "引擎就绪" : "连接中"}</span>
      </div>
      <button type="button" className="button button--compact" onClick={onStart}>
        开始采集
        <ArrowUpRight size={15} aria-hidden="true" />
      </button>
    </nav>
  );
}
