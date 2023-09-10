git clone --depth 1 git@github.com:vam-google/tensorflow.git

cd tensorflow/tensorflow
find . -name BUILD -exec truncate -s 0 {} \; # do not touch third_party deps
bazel build //tensorflow:libtensorflow_framework.so.2.14.0

bazel cquery --config=pycpp_filters 'deps("//tensorflow:libtensorflow_cc.so.2.14.0")' --output label_kind | sort | cut -d ' ' -f 1 | uniq
bazel cquery --config=pycpp_filters 'deps("//tensorflow:libtensorflow_cc.so.2.14.0")' --output build

#cat _/all_tests.txt | sort | cut -d ' ' -f 1 | awk '{gsub(/\n/," "); print $0}' | sort | uniq -c | sort -nr


# List of parsable targets libtensorflow_cc.so.2.14.0-only
bazel cquery --config=pycpp_filters \
  'deps(//tensorflow:libtensorflow_cc.so.2.14.0)' \
  --keep_going \
  --output label_kind \
  -- \
  -//tensorflow/python/integration_testing/... \
  -//tensorflow/compiler/tf2tensorrt/... \
  -//tensorflow/compiler/xrt/... \
  -//tensorflow/core/tpu/... \
  -//tensorflow/lite/... \
  -//tensorflow/tools/toolchains/... \
  | grep " //" \
  | sed 's, [^ ]*$,,' \
  | sort \
  | uniq | grep -E -v "(source file)|(generated file)"


# List of parsable targets
bazel cquery --config=pycpp_filters \
  'deps(//tensorflow/...)' \
  --keep_going \
  --output label_kind \
  -- \
  -//tensorflow/python/integration_testing/... \
  -//tensorflow/compiler/tf2tensorrt/... \
  -//tensorflow/compiler/xrt/... \
  -//tensorflow/core/tpu/... \
  -//tensorflow/lite/... \
  -//tensorflow/tools/toolchains/... \
  | grep " //" \
  | sed 's, [^ ]*$,,' \
  | sort \
  | uniq | grep -E -v "(source file)|(generated file)"

# internal and external group by target kind
bazel cquery --config=pycpp_filters 'deps(//tensorflow/...)' \
  --keep_going \
  --output label_kind \
  -- \
  -//tensorflow/python/integration_testing/... \
  -//tensorflow/compiler/tf2tensorrt/... \
  -//tensorflow/compiler/xrt/... \
  -//tensorflow/core/tpu/... \
  -//tensorflow/lite/... \
  -//tensorflow/tools/toolchains/... \
  | sed 's, [^ ]*$,,' \
  | sort \
  | uniq \
  | cut -d ' ' -f 1 \
  | sort \
  | awk '{gsub(/\n/," "); print $0}' \
  | sort \
  | uniq -c \
  | sort -nr

# internal only group by target kind
bazel cquery \
  --config=pycpp_filters \
  'deps(//tensorflow/...)' \
  --keep_going \
  --output label_kind \
  -- \
  -//tensorflow/python/integration_testing/... \
  -//tensorflow/compiler/tf2tensorrt/... \
  -//tensorflow/compiler/xrt/... \
  -//tensorflow/core/tpu/... \
  -//tensorflow/lite/... \
  -//tensorflow/tools/toolchains/... \
  | grep " //" \
  | sed 's, [^ ]*$,,' \
  | sort \
  | uniq \
  | cut -d ' ' -f 1 \
  | sort \
  | awk '{gsub(/\n/," "); print $0}' \
  | sort \
  | uniq -c \
  | sort -nr


bazel cquery \
  --config=pycpp_filters \
  'deps(//tensorflow/...)' \
  --keep_going \
  --output build \
  -- \
  -//tensorflow/python/integration_testing/... \
  -//tensorflow/compiler/tf2tensorrt/... \
  -//tensorflow/compiler/xrt/... \
  -//tensorflow/core/tpu/... \
  -//tensorflow/lite/... \
  -//tensorflow/tools/toolchains/...

clang -I. -Xclang -ast-dump main.cc -fsyntax-only  -fno-color-diagnostics > _/main_ast_no_namespace.txt
clang -I. -Xclang -ast-dump main.cc -fsyntax-only  -fno-color-diagnostics | grep -P "(static cinit$)|(\)' static$)|(NamespaceDecl .* line:\d+:\d+$)"
cat stderr-5 | grep -P "error: " | sed 's/:[0-9]*//g' | sort | uniq | sort -nr > sorted.txt
cat stderr-5 | grep -P "error: " | cut -d ':' -f 1 | sort | uniq -c | sort -nr > sorted1.txt