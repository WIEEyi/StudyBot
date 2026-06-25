"use client";

/**
 * 知识图谱可视化组件
 *
 * 基于 vis-network standalone 封装：
 * - 通过 useRef + useEffect 管理 DOM 生命周期
 * - 支持节点点击回调
 * - 不同 category 使用不同颜色
 * - 不同 relation_type 使用不同边样式
 */
import { useEffect, useRef } from "react";
import { Network, DataSet } from "vis-network/standalone";
import type { GraphNode, GraphEdge } from "@/lib/types";

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeClick?: (nodeId: number) => void;
  height?: string;
}

/** 分类 → 颜色映射 */
const CATEGORY_COLORS: Record<string, string> = {
  subject: "#3B82F6",  // blue
  topic: "#10B981",    // green
  subtopic: "#8B5CF6", // purple
  term: "#F59E0B",     // amber
  other: "#6B7280",    // gray
};

/** 关系类型 → 边样式 */
const EDGE_STYLES: Record<string, { color: string; dashes: boolean }> = {
  prerequisite: { color: "#EF4444", dashes: false },  // red solid
  related: { color: "#6B7280", dashes: true },        // gray dashed
  part_of: { color: "#3B82F6", dashes: false },       // blue solid
};

export default function KnowledgeGraphCanvas({
  nodes,
  edges,
  onNodeClick,
  height = "500px",
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);

  useEffect(() => {
    if (!containerRef.current || nodes.length === 0) return;

    // 构建节点数据集
    const nodeDataset = new DataSet(
      nodes.map((n) => ({
        id: n.id,
        label: n.name,
        color: {
          background: CATEGORY_COLORS[n.category] || CATEGORY_COLORS.other,
          border: "#ffffff",
          highlight: {
            background: CATEGORY_COLORS[n.category] || CATEGORY_COLORS.other,
            border: "#1F2937",
          },
        },
        font: {
          size: 14,
          color: "#ffffff",
          face: "system-ui, sans-serif",
        },
        borderWidth: 2,
        shape: "box",
        margin: { top: 10, bottom: 10, left: 14, right: 14 },
        shapeProperties: {
          borderRadius: 6,
        },
      }))
    );

    // 构建边数据集
    const edgeDataset = new DataSet(
      edges.map((e) => {
        const style = EDGE_STYLES[e.relation_type] || EDGE_STYLES.related;
        return {
          from: e.source,
          to: e.target,
          label: e.label,
          arrows: "to",
          color: { color: style.color, highlight: style.color },
          dashes: style.dashes,
          font: {
            size: 10,
            color: "#6B7280",
            background: "#ffffff",
            strokeWidth: 2,
          },
          smooth: {
            type: "curvedCW",
            roundness: 0.2,
          },
          width: 1.5,
        };
      })
    );

    const options = {
      physics: {
        solver: "forceAtlas2Based",
        forceAtlas2Based: {
          gravitationalConstant: -35,
          centralGravity: 0.005,
          springLength: 160,
          springConstant: 0.08,
        },
        stabilization: {
          iterations: 100,
        },
      },
      interaction: {
        hover: true,
        tooltipDelay: 200,
        zoomView: true,
        dragView: true,
        navigationButtons: false,
      },
      edges: {
        arrows: {
          to: { scaleFactor: 0.8 },
        },
      },
    };

    const network = new Network(
      containerRef.current,
      { nodes: nodeDataset, edges: edgeDataset },
      options
    );
    networkRef.current = network;

    // 节点点击事件
    if (onNodeClick) {
      network.on("click", (params: Record<string, unknown>) => {
        const clickedNodes = params.nodes as number[] | undefined;
        if (clickedNodes && clickedNodes.length === 1) {
          onNodeClick(clickedNodes[0]);
        }
      });
    }

    // 稳定后自动适配视图
    network.once("stabilizationIterationsDone", () => {
      network.fit({
        animation: {
          duration: 500,
          easingFunction: "easeInOutQuad",
        },
      });
    });

    return () => {
      network.destroy();
      networkRef.current = null;
    };
  }, [nodes, edges, onNodeClick]);

  // 空状态
  if (nodes.length === 0) {
    return (
      <div
        style={{ width: "100%", height }}
        className="border border-gray-200 rounded-xl bg-white flex items-center justify-center"
      >
        <div className="text-center text-gray-400">
          <p className="text-4xl mb-3">🕸️</p>
          <p>还没有概念节点</p>
          <p className="text-sm mt-1">创建概念并添加关系后，图谱将在这里显示</p>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height }}
      className="border border-gray-200 rounded-xl bg-white"
    />
  );
}
