import type { Plugin } from "vite";
export function prohibitedModule(id: string) {
  return (
    /(?:^|[/\\])(?:fixtures|tests|__tests__|dev)(?:[/\\]|$)/.test(id) ||
    /(?:research-preview|analysis[/\\]results|lib[/\\]research\.ts)/.test(id)
  );
}
export function fixtureGuard(): Plugin {
  return {
    name: "solarloss-production-fixture-guard",
    apply: "build",
    moduleParsed(module) {
      if (prohibitedModule(module.id))
        this.error(`Production fixture import prohibited: ${module.id}`);
    },
    generateBundle(_options, bundle) {
      for (const entry of Object.values(bundle)) {
        if (
          entry.type === "chunk" &&
          Object.keys(entry.modules).some(prohibitedModule)
        )
          this.error(`Prohibited fixture in ${entry.fileName}`);
      }
    },
  };
}
