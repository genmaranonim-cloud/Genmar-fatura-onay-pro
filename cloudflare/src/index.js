import { DurableObject } from "cloudflare:workers";

export class GenmarContainer extends DurableObject {
  starting;

  async fetch(request) {
    this.starting ??= this.startAndWait().finally(() => {
      this.starting = undefined;
    });
    await this.starting;

    const original = new URL(request.url);
    const target = new URL(request.url);
    target.protocol = "http:";
    target.host = "container";
    const forwarded = new Request(target, request);
    forwarded.headers.delete("host");
    forwarded.headers.set("x-forwarded-host", original.host);
    forwarded.headers.set("x-forwarded-proto", original.protocol.slice(0, -1));
    return this.ctx.container.getTcpPort(8080).fetch(forwarded);
  }

  async startAndWait() {
    const container = this.ctx.container;
    if (!container.running) {
      container.start({
        image: container.images.app,
        instance: "lite",
        enableInternet: true,
        env: {
          PORT: "8080",
          CLOUDFLARE_APPLICATION_ID: "genmar-fatura-onay-pro",
          PRO_DATA_DIR: "/data/genmar-pro",
          PRO_ADMIN_PASSWORD: this.env.PRO_ADMIN_PASSWORD,
          PRO_SECRET_KEY: this.env.PRO_SECRET_KEY,
          R2_ENDPOINT: this.env.R2_ENDPOINT,
          R2_BUCKET: this.env.R2_BUCKET,
          R2_ACCESS_KEY_ID: this.env.R2_ACCESS_KEY_ID,
          R2_SECRET_ACCESS_KEY: this.env.R2_SECRET_ACCESS_KEY,
        },
      });
    }

    await container.setInactivityTimeout(10 * 60 * 1000);
    const port = container.getTcpPort(8080);
    let lastError;
    for (let attempt = 0; attempt < 150; attempt++) {
      try {
        const response = await port.fetch("http://container/health", {
          signal: AbortSignal.timeout(1000),
        });
        await response.body?.cancel();
        if (response.ok) return;
        lastError = new Error(`Health check returned ${response.status}`);
      } catch (error) {
        lastError = error;
      }
      await scheduler.wait(200);
    }
    throw new Error("GENMAR container did not become ready", { cause: lastError });
  }
}

export default {
  fetch(request, env) {
    return env.GENMAR_CONTAINER.getByName("genmar-primary").fetch(request);
  },
};
