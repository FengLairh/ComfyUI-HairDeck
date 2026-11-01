import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

function outputUrl(file) {
    const query = new URLSearchParams({ filename: file.filename, subfolder: file.subfolder ?? "", type: "output" });
    return api.apiURL(`/view?${query.toString()}`);
}

app.registerExtension({
    name: "HairDeck.Outputs",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "HairDeckSave") return;
        const previous = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (message) {
            previous?.apply(this, arguments);
            if (!Array.isArray(message.hairdeck_files)) return;
            if (!this.hairdeckOutputPanel) {
                const panel = document.createElement("div");
                panel.style.cssText = "box-sizing:border-box;padding:10px;background:var(--comfy-menu-bg,#242424);color:var(--input-text,#eee);font:12px sans-serif;overflow:auto;border-radius:6px;";
                this.hairdeckOutputPanel = panel;
                this.addDOMWidget("hairdeck_outputs", "hairdeck_outputs", panel, {
                    serialize: false,
                    getMinHeight: () => 150,
                    getMaxHeight: () => 410,
                });
            }
            const panel = this.hairdeckOutputPanel;
            panel.replaceChildren();
            const title = document.createElement("div");
            title.textContent = Array.isArray(message.hairdeck_summary)
                ? message.hairdeck_summary.join("\n") : message.hairdeck_summary ?? "保存完成";
            title.style.marginBottom = "10px";
            panel.append(title);
            for (const file of message.hairdeck_files) {
                const link = document.createElement("a");
                link.href = outputUrl(file);
                link.download = file.filename;
                link.textContent = file.label ?? file.filename;
                link.style.cssText = "display:inline-block;margin:0 8px 8px 0;padding:5px 8px;border:1px solid #777;border-radius:5px;color:inherit;text-decoration:none;";
                panel.append(link);
            }
            const movie = message.hairdeck_files.find((file) => file.kind === "video");
            if (movie) {
                const video = document.createElement("video");
                video.controls = true;
                video.loop = true;
                video.muted = true;
                video.preload = "metadata";
                video.src = outputUrl(movie);
                video.style.cssText = "display:block;width:100%;max-height:260px;background:#111;border-radius:5px;";
                panel.append(video);
            }
            this.setSize([Math.max(this.size[0], 400), Math.max(this.size[1], movie ? 650 : 470)]);
            this.graph?.setDirtyCanvas(true, true);
        };
        const removed = nodeType.prototype.onRemoved;
        nodeType.prototype.onRemoved = function () {
            this.hairdeckOutputPanel?.querySelector("video")?.pause();
            removed?.apply(this, arguments);
        };
    },
});
