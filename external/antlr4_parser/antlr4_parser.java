import java.io.*;
import java.lang.management.ManagementFactory;
import java.lang.management.MemoryMXBean;
import java.util.*;
import java.util.List;

import org.antlr.v4.runtime.*;
import org.antlr.v4.runtime.tree.*;

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
        if (str == null) return "";
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
 * 内存使用监控类
 */
class MemoryMonitor {
    private MemoryMXBean memoryBean;
    private long initialMemory;

    public MemoryMonitor() {
        memoryBean = ManagementFactory.getMemoryMXBean();
        initialMemory = getCurrentMemory();
    }

    private long getCurrentMemory() {
        return memoryBean.getHeapMemoryUsage().getUsed() / 1024; // KB
    }

    public long getMemoryDiff() {
        long current = getCurrentMemory();
        return Math.max(0, current - initialMemory);
    }
}

/**
 * AST节点计数器
 */
class ASTNodeCounter {
    
    public static long countNodes(ParseTree tree) {
        if (tree == null) return 0;
        
        long count = 1; // 当前节点
        
        // 递归计算子节点
        for (int i = 0; i < tree.getChildCount(); i++) {
            count += countNodes(tree.getChild(i));
        }
        
        return count;
    }
    
    public static long countAllNodes(List<ParseTree> trees) {
        long total = 0;
        for (ParseTree tree : trees) {
            total += countNodes(tree);
        }
        return total;
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
 * ANTLR4 SMT解析器类
 */
class ANTLR4SMTParser {
    
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
            
            // 创建输入流
            CharStream input = CharStreams.fromFileName(filename);
            
            // 创建词法分析器
            SMTLIBv2Lexer lexer = new SMTLIBv2Lexer(input);
            
            // 创建token流
            CommonTokenStream tokens = new CommonTokenStream(lexer);
            
            // 创建解析器
            SMTLIBv2Parser parser = new SMTLIBv2Parser(tokens);
            
            // 设置错误处理
            List<String> parseErrors = new ArrayList<>();
            parser.removeErrorListeners();
            parser.addErrorListener(new BaseErrorListener() {
                @Override
                public void syntaxError(Recognizer<?, ?> recognizer, Object offendingSymbol,
                                      int line, int charPositionInLine, String msg, RecognitionException e) {
                    parseErrors.add("语法错误 第" + line + "行:" + charPositionInLine + " " + msg);
                }
            });
            
            // 解析文件
            ParseTree tree = parser.script();
            
            // 检查解析错误
            if (!parseErrors.isEmpty()) {
                result.errors.addAll(parseErrors);
                if (tree == null) {
                    result.parsingMethod = "antlr4_failed";
                    return result;
                }
            }
            
            // 解析成功
            result.success = true;
            result.parsingMethod = "antlr4_parse_tree";
            
            // 计算AST节点数
            result.astNodeCount = ASTNodeCounter.countNodes(tree);
            
            // 如果没有节点，至少应该有1个根节点
            if (result.astNodeCount == 0 && tree != null) {
                result.astNodeCount = 1;
            }
            
        } catch (IOException e) {
            result.errors.add("文件读取错误: " + e.getMessage());
        } catch (RecognitionException e) {
            result.errors.add("ANTLR4解析异常: " + e.getMessage());
        } catch (Exception e) {
            result.errors.add("解析过程异常: " + e.getMessage());
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
public class antlr4_parser {
    
    public static void main(String[] args) {
        if (args.length != 1) {
            JSONOutput json = new JSONOutput();
            json.addField("success", false);
            json.addField("parse_time", 0.0);
            json.addField("memory_usage", 0L);
            json.addField("ast_node_count", 0L);
            
            List<String> errors = new ArrayList<>();
            errors.add("用法: " + antlr4_parser.class.getSimpleName() + " <smt_file>");
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
            ANTLR4SMTParser parser = new ANTLR4SMTParser();
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