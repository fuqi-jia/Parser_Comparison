import java.io.*;
import java.lang.management.ManagementFactory;
import java.lang.management.MemoryMXBean;
import java.util.*;
import java.util.List;

import org.smtlib.*;
import org.smtlib.IExpr.*;

/**
 * JSON输出辅助类
 */
class JSONOutput {
    private StringBuilder sb;
    private boolean firstField;

    public JSONOutput() {
        sb = new StringBuilder();
        firstField = true;
        sb.append("{");
    }

    public void addField(String name, boolean value) {
        if (!firstField) sb.append(",");
        sb.append("\"").append(name).append("\":").append(value);
        firstField = false;
    }

    public void addField(String name, double value) {
        if (!firstField) sb.append(",");
        sb.append("\"").append(name).append("\":").append(value);
        firstField = false;
    }

    public void addField(String name, long value) {
        if (!firstField) sb.append(",");
        sb.append("\"").append(name).append("\":").append(value);
        firstField = false;
    }

    public void addField(String name, String value) {
        if (!firstField) sb.append(",");
        sb.append("\"").append(name).append("\":\"").append(escapeJson(value)).append("\"");
        firstField = false;
    }

    public void addArrayField(String name, List<String> values) {
        if (!firstField) sb.append(",");
        sb.append("\"").append(name).append("\":[");
        for (int i = 0; i < values.size(); i++) {
            if (i > 0) sb.append(",");
            sb.append("\"").append(escapeJson(values.get(i))).append("\"");
        }
        sb.append("]");
        firstField = false;
    }

    @Override
    public String toString() {
        return sb.toString() + "}";
    }

    private String escapeJson(String str) {
        return str.replace("\\", "\\\\")
                 .replace("\"", "\\\"")
                 .replace("\b", "\\b")
                 .replace("\f", "\\f")
                 .replace("\n", "\\n")
                 .replace("\r", "\\r")
                 .replace("\t", "\\t");
    }
}

/**
 * 内存监控类
 */
class MemoryMonitor {
    private MemoryMXBean memoryBean;
    private long initialMemory;

    public MemoryMonitor() {
        memoryBean = ManagementFactory.getMemoryMXBean();
        initialMemory = getCurrentMemory();
    }

    private long getCurrentMemory() {
        return memoryBean.getHeapMemoryUsage().getUsed() / 1024; // 转换为KB
    }

    public long getMemoryDiff() {
        long current = getCurrentMemory();
        return Math.max(0, current - initialMemory);
    }
}
class ASTNodeCounter {

    public static long countNodes(IExpr expr) {
        return countNodes(expr, new HashSet<>());
    }

    private static long countNodes(IExpr expr, Set<IExpr> visited) {
        if (expr == null) return 0;
        if (visited.contains(expr)) return 0;
        visited.add(expr);

        long count = 1; // 当前节点

        try {
            if (expr instanceof IFcnExpr) {
                for (IExpr arg : ((IFcnExpr) expr).args()) {
                    count += countNodes(arg, visited);
                }
            } else if (expr instanceof ILet) {
                ILet let = (ILet) expr;
                count += countNodes(let.expr(), visited);
                for (IBinding binding : let.bindings()) {
                    count += countNodes(binding.expr(), visited);
                }
            } else if (expr instanceof IForall) {
                count += countNodes(((IForall) expr).expr(), visited);
            } else if (expr instanceof IExists) {
                count += countNodes(((IExists) expr).expr(), visited);
            } else if (expr instanceof IAttributedExpr) {
                count += countNodes(((IAttributedExpr) expr).expr(), visited);
            }
            // 其他节点类型：符号、字面量，不需要递归
        } catch (Exception e) {
            // 忽略异常，返回当前已统计的 count
        }

        return count;
    }

    public static long countCommandNodes(ICommand command) {
        if (command == null) return 0;

        long count = 1;

        try {
            if (command instanceof org.smtlib.command.C_assert) {
                IExpr expr = ((org.smtlib.command.C_assert) command).expr();
                count += countNodes(expr);
            }
        } catch (Exception e) {
            // 忽略异常
        }

        return count;
    }
}


/**
 * 解析结果结构
 */
class ParseResult {
    public boolean success = false;
    public double parseTime = 0.0; // 毫秒
    public long memoryUsage = 0; // KB
    public long astNodeCount = 0;
    public List<String> errors = new ArrayList<>();
    public String parsingMethod = "";
}

/**
 * jSMTLIB SMT解析器类
 */
class JSMTLIBParser {
    
    public ParseResult parseFile(String filename) {
        ParseResult result = new ParseResult();
        MemoryMonitor memoryMonitor = new MemoryMonitor();
        
        // 开始计时
        long startTime = System.nanoTime();
        
        try {
            // 检查文件是否存在
            File file = new File(filename);
            if (!file.exists()) {
                result.errors.add("文件不存在: " + filename);
                return result;
            }
            
            // 创建SMT对象
            SMT smt = new SMT();
            
            // 创建文件输入源
            Reader reader = new BufferedReader(new FileReader(file));
            ISource source = smt.smtConfig.smtFactory.createSource(
                new CharSequenceReader(reader, 100000, 0, 2), filename);
            IParser parser = smt.smtConfig.smtFactory.createParser(smt.smtConfig, source);
            
            result.parsingMethod = "jsmtlib_parser";
            long totalNodes = 0;
            
            // 解析所有命令
            while (!parser.isEOD()) {
                try {
                    ICommand command = parser.parseCommand();
                    if (command == null) {
                        // 解析错误
                        IResponse lastError = parser.lastError();
                        if (lastError != null) {
                            result.errors.add("解析错误: " + lastError.toString());
                        }
                        continue;
                    }
                    
                    // 统计AST节点数
                    totalNodes += ASTNodeCounter.countCommandNodes(command);
                    
                } catch (IParser.ParserException e) {
                    result.errors.add("解析异常: " + e.getMessage());
                } catch (Exception e) {
                    result.errors.add("未知异常: " + e.getMessage());
                }
            }
            
            result.astNodeCount = totalNodes;
            result.success = true;
            
        } catch (FileNotFoundException e) {
            result.errors.add("文件未找到: " + e.getMessage());
        } catch (IOException e) {
            result.errors.add("IO异常: " + e.getMessage());
        } catch (Exception e) {
            result.errors.add("程序异常: " + e.getMessage());
        }
        
        // 结束计时
        long endTime = System.nanoTime();
        result.parseTime = (endTime - startTime) / 1_000_000.0; // 转换为毫秒
        
        // 计算内存使用
        result.memoryUsage = memoryMonitor.getMemoryDiff();
        
        return result;
    }
}

/**
 * 主类
 */
public class jsmtlib_parser {
    
    public static void main(String[] args) {
        if (args.length != 1) {
            JSONOutput json = new JSONOutput();
            json.addField("success", false);
            json.addField("parse_time", 0.0);
            json.addField("memory_usage", 0L);
            json.addField("ast_node_count", 0L);
            
            List<String> errors = new ArrayList<>();
            errors.add("用法: java jsmtlib_parser <smt_file>");
            if (args.length > 0) {
                StringBuilder argsStr = new StringBuilder("接收到的参数: ");
                for (int i = 0; i < args.length; i++) {
                    if (i > 0) argsStr.append(" ");
                    argsStr.append(args[i]);
                }
                errors.add(argsStr.toString());
            }
            json.addArrayField("errors", errors);
            
            System.out.println(json.toString());
            System.exit(1);
        }
        
        String filename = args[0];
        
        try {
            JSMTLIBParser parser = new JSMTLIBParser();
            ParseResult result = parser.parseFile(filename);
            
            // 输出JSON结果
            JSONOutput json = new JSONOutput();
            json.addField("success", result.success);
            json.addField("parse_time", result.parseTime);
            json.addField("memory_usage", result.memoryUsage);
            json.addField("ast_node_count", result.astNodeCount);
            json.addArrayField("errors", result.errors);
            
            if (!result.parsingMethod.isEmpty()) {
                json.addField("parsing_method", result.parsingMethod);
            }
            
            System.out.println(json.toString());
            
            System.exit(result.success ? 0 : 1);
            
        } catch (Exception e) {
            JSONOutput json = new JSONOutput();
            json.addField("success", false);
            json.addField("parse_time", 0.0);
            json.addField("memory_usage", 0L);
            json.addField("ast_node_count", 0L);
            
            List<String> errors = new ArrayList<>();
            errors.add("程序异常: " + e.getMessage());
            json.addArrayField("errors", errors);
            
            System.out.println(json.toString());
            System.exit(1);
        }
    }
}
