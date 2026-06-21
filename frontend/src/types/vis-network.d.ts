/**
 * vis-network standalone 最小类型声明
 *
 * vis-network 没有官方的 TypeScript 类型包，
 * 这里只声明我们需要的 API。
 */

declare module "vis-network/standalone" {
  export class DataSet<T = Record<string, unknown>> {
    constructor(items: T[]);
    add(items: T | T[]): void;
    remove(id: number | string): void;
    update(item: T): void;
    get(id: number | string): T | null;
    getIds(): (number | string)[];
    forEach(callback: (item: T, id: number | string) => void): void;
    readonly length: number;
  }

  export interface NetworkOptions {
    physics?: {
      solver?: string;
      forceAtlas2Based?: {
        gravitationalConstant?: number;
        centralGravity?: number;
        springLength?: number;
        springConstant?: number;
      };
      stabilization?: {
        iterations?: number;
      };
    };
    interaction?: {
      hover?: boolean;
      tooltipDelay?: number;
      zoomView?: boolean;
      dragView?: boolean;
    };
    edges?: {
      arrows?: {
        to?: {
          scaleFactor?: number;
        };
      };
    };
  }

  export interface NetworkData {
    nodes: DataSet<Record<string, unknown>>;
    edges: DataSet<Record<string, unknown>>;
  }

  export class Network {
    constructor(
      container: HTMLElement,
      data: NetworkData,
      options?: NetworkOptions
    );
    destroy(): void;
    on(event: string, callback: (params: Record<string, unknown>) => void): void;
    once(event: string, callback: (params: Record<string, unknown>) => void): void;
    fit(options?: { animation?: { duration?: number; easingFunction?: string } }): void;
    setData(data: NetworkData): void;
  }
}
