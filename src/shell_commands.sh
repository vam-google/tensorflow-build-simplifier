git clone --depth 1 git@github.com:vam-google/tensorflow.git

cd tensorflow/tensorflow
find . -name BUILD -exec truncate -s 0 {} \; # do not touch third_party deps
bazel build //tensorflow:libtensorflow_framework.so.2.14.0

bazel cquery --config=pycpp_filters 'deps("//tensorflow:libtensorflow_cc.so.2.14.0")' --output label_kind | sort | cut -d ' ' -f 1 | uniq
bazel cquery --config=pycpp_filters 'deps("//tensorflow:libtensorflow_cc.so.2.14.0")' --output build

#cat _/all_tests.txt | sort | cut -d ' ' -f 1 | awk '{gsub(/\n/," "); print $0}' | sort | uniq -c | sort -nr

# all interna + external targets via deps
bazel cquery --config=pycpp_filters 'deps(//tensorflow/...)' --keep_going --output label_kind | cut -d ' ' -f 1 | sort | awk '{gsub(/\n/," "); print $0}' | sort | uniq -c | sort -nr
# all interna targets via deps
bazel cquery --config=pycpp_filters 'deps(//tensorflow/...)' --keep_going --output label_kind | grep " //" | cut -d ' ' -f 1 | sort | awk '{gsub(/\n/," "); print $0}' | sort | uniq -c | sort -nr
# all internal targets
bazel cquery --config=pycpp_filters '//tensorflow/...' --keep_going --output label_kind | cut -d ' ' -f 1 | sort | awk '{gsub(/\n/," "); print $0}' | sort | uniq -c | sort -nr
