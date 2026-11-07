import { BrandMark } from "./BrandMark";

export function Footer() {
  return (
    <footer className="footer">
      <p className="footer__statement">人脸数据留在本机，训练与识别都由你控制。</p>
      <div className="footer__meta">
        <BrandMark compact />
        <span>CNN Face Workbench · MIT</span>
      </div>
    </footer>
  );
}
